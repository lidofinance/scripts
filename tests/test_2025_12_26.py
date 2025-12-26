from brownie import web3, interface, chain, reverts
from brownie.network.transaction import TransactionReceipt

from utils.test.tx_tracing_helpers import group_voting_events_from_receipt
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id, create_vote
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
)
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grant_event,
    validate_permission_revoke_event,
)
from utils.test.event_validators.token_manager import (
    Burn,
    validate_ldo_burn_event,
    Issue,
    validate_ldo_issue_event,
    Vested,
    validate_ldo_vested_event,
)


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2025_12_26 import start_vote, get_vote_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================

VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
TOKEN_MANAGER = "0xf73a1260d222f447210581DDf212D915c09a3249"
ACL = "0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb"

SOURCE_ADDRESS = "0xa8107de483f9623390d543b77c8e4bbb6f7af752"
SOURCE_LDO = 48_934_690_0011 * 10**14  # 48,934,690.0011 LDO

# TODO update targets and amounts
TARGET_ADDRESSES = [
    "0x396343362be2a4da1ce0c1c210945346fb82aa49",
    "0xbcb61ad7b2d7949ecaefc77adbd5914813aeeffa",
    "0x1b5662b2a1831cc9f743101d15ab5900512c82a4",
    "0xb79645264d73ad520a1ba87e5d69a15342a6270f",
    "0x28c61ce51e4c3ada729a903628090fa90dc21d60",
]
TARGET_LDOS = [
    10_000_000 * 10**18,
    10_000_000 * 10**18,
    10_000_000 * 10**18,
    10_000_000 * 10**18,
    8_934_690_0011 * 10**14,
]

VESTING_START = 1767200400 # Wed Dec 31 2025 17:00:00 GMT+0000
VESTING_CLIFF = 1798736400 # Thu Dec 31 2026 17:00:00 GMT+0000
VESTING_TOTAL = VESTING_CLIFF
IS_REVOKABLE = True

BURN_ROLE = "BURN_ROLE"
ISSUE_ROLE = "ISSUE_ROLE"

LDO_TOKEN = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"

EXPECTED_VOTE_ID = 197
EXPECTED_VOTE_EVENTS_COUNT = 11
# TODO update description hash
IPFS_DESCRIPTION_HASH = "bafkreigx3ltavpe45fqk723ikgxlfom36icba5zyrojlflclf6h2vn5tw4"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    acl = interface.ACL(ACL)
    ldo_token = interface.ERC20(LDO_TOKEN)
    token_manager = interface.TokenManager(TOKEN_MANAGER)
    stranger = accounts[0]


    # =========================================================================
    # ======================== Identify or Create vote ========================
    # =========================================================================
    if vote_ids_from_env:
        vote_id = vote_ids_from_env[0]
        if EXPECTED_VOTE_ID is not None:
            assert vote_id == EXPECTED_VOTE_ID
    elif EXPECTED_VOTE_ID is not None and voting.votesLength() > EXPECTED_VOTE_ID:
        vote_id = EXPECTED_VOTE_ID
    else:
        vote_id, _ = start_vote({"from": ldo_holder}, silent=True)

    _, call_script_items = get_vote_items()
    onchain_script = voting.getVote(vote_id)["script"]
    assert onchain_script == encode_call_script(call_script_items)


    # =========================================================================
    # ============================= Execute Vote ==============================
    # =========================================================================
    is_executed = voting.getVote(vote_id)["executed"]
    if not is_executed:
        # =======================================================================
        # ========================= Before voting checks ========================
        # =======================================================================

        # sanity checks
        assert len(TARGET_ADDRESSES) == len(TARGET_LDOS)
        assert all(ldo > 0 for ldo in TARGET_LDOS)
        assert sum(TARGET_LDOS) == SOURCE_LDO

        # Items 1,3
        assert not acl.hasPermission(VOTING, TOKEN_MANAGER, web3.keccak(text=BURN_ROLE).hex())

        # Item 2
        assert ldo_token.balanceOf(SOURCE_ADDRESS) == SOURCE_LDO

        # Items 4,6
        assert not acl.hasPermission(VOTING, TOKEN_MANAGER, web3.keccak(text=ISSUE_ROLE).hex())

        # Item 5
        token_manager_ldo_balance_before = ldo_token.balanceOf(TOKEN_MANAGER)
        tm_ldo_balance_before = ldo_token.balanceOf(TOKEN_MANAGER)
        ldo_supply_before = ldo_token.totalSupply()

        # Items 7-11
        target_address_0_ldo_balance_before = ldo_token.balanceOf(TARGET_ADDRESSES[0])
        target_address_1_ldo_balance_before = ldo_token.balanceOf(TARGET_ADDRESSES[1])
        target_address_2_ldo_balance_before = ldo_token.balanceOf(TARGET_ADDRESSES[2])
        target_address_3_ldo_balance_before = ldo_token.balanceOf(TARGET_ADDRESSES[3])
        target_address_4_ldo_balance_before = ldo_token.balanceOf(TARGET_ADDRESSES[4])
        target_address_0_vestings_length_before = token_manager.vestingsLengths(TARGET_ADDRESSES[0])
        target_address_1_vestings_length_before = token_manager.vestingsLengths(TARGET_ADDRESSES[1])
        target_address_2_vestings_length_before = token_manager.vestingsLengths(TARGET_ADDRESSES[2])
        target_address_3_vestings_length_before = token_manager.vestingsLengths(TARGET_ADDRESSES[3])
        target_address_4_vestings_length_before = token_manager.vestingsLengths(TARGET_ADDRESSES[4])
        target_address_0_spendable_balance_before = token_manager.spendableBalanceOf(TARGET_ADDRESSES[0])
        target_address_1_spendable_balance_before = token_manager.spendableBalanceOf(TARGET_ADDRESSES[1])
        target_address_2_spendable_balance_before = token_manager.spendableBalanceOf(TARGET_ADDRESSES[2])
        target_address_3_spendable_balance_before = token_manager.spendableBalanceOf(TARGET_ADDRESSES[3])
        target_address_4_spendable_balance_before = token_manager.spendableBalanceOf(TARGET_ADDRESSES[4])

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH
        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        # Items 1,3
        assert not acl.hasPermission(VOTING, TOKEN_MANAGER, web3.keccak(text=BURN_ROLE).hex())

        # Item 2
        assert ldo_token.balanceOf(SOURCE_ADDRESS) == 0

        # Items 4,6
        assert not acl.hasPermission(VOTING, TOKEN_MANAGER, web3.keccak(text=ISSUE_ROLE).hex())

        # Item 5
        assert ldo_token.balanceOf(TOKEN_MANAGER) == token_manager_ldo_balance_before
        assert ldo_token.totalSupply() == ldo_supply_before
        assert ldo_token.balanceOf(TOKEN_MANAGER) == tm_ldo_balance_before

        # Items 7-11
        assert ldo_token.balanceOf(TARGET_ADDRESSES[0]) == target_address_0_ldo_balance_before + TARGET_LDOS[0]
        assert ldo_token.balanceOf(TARGET_ADDRESSES[1]) == target_address_1_ldo_balance_before + TARGET_LDOS[1]
        assert ldo_token.balanceOf(TARGET_ADDRESSES[2]) == target_address_2_ldo_balance_before + TARGET_LDOS[2]
        assert ldo_token.balanceOf(TARGET_ADDRESSES[3]) == target_address_3_ldo_balance_before + TARGET_LDOS[3]
        assert ldo_token.balanceOf(TARGET_ADDRESSES[4]) == target_address_4_ldo_balance_before + TARGET_LDOS[4]
        assert token_manager.vestingsLengths(TARGET_ADDRESSES[0]) == target_address_0_vestings_length_before + 1
        assert token_manager.vestingsLengths(TARGET_ADDRESSES[1]) == target_address_1_vestings_length_before + 1
        assert token_manager.vestingsLengths(TARGET_ADDRESSES[2]) == target_address_2_vestings_length_before + 1
        assert token_manager.vestingsLengths(TARGET_ADDRESSES[3]) == target_address_3_vestings_length_before + 1
        assert token_manager.vestingsLengths(TARGET_ADDRESSES[4]) == target_address_4_vestings_length_before + 1
        assert token_manager.spendableBalanceOf(TARGET_ADDRESSES[0]) == target_address_0_spendable_balance_before
        assert token_manager.spendableBalanceOf(TARGET_ADDRESSES[1]) == target_address_1_spendable_balance_before
        assert token_manager.spendableBalanceOf(TARGET_ADDRESSES[2]) == target_address_2_spendable_balance_before
        assert token_manager.spendableBalanceOf(TARGET_ADDRESSES[3]) == target_address_3_spendable_balance_before
        assert token_manager.spendableBalanceOf(TARGET_ADDRESSES[4]) == target_address_4_spendable_balance_before
        for idx, target_address in enumerate(TARGET_ADDRESSES):
            vesting = token_manager.getVesting(target_address, token_manager.vestingsLengths(target_address) - 1)
            assert vesting["amount"] == TARGET_LDOS[idx]
            assert vesting["start"] == VESTING_START
            assert vesting["cliff"] == VESTING_CLIFF
            assert vesting["vesting"] == VESTING_TOTAL
            assert vesting["revokable"] == IS_REVOKABLE

        # scenario tests
        move_ldo_test(stranger, ldo_token, token_manager)
        can_vote_with_vesting(ldo_holder, ldo_token, stranger, voting)

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        validate_permission_grant_event(
            event=vote_events[0],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=VOTING,
                role=web3.keccak(text=BURN_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_ldo_burn_event(
            event=vote_events[1],
            b=Burn(
                holder_addr=SOURCE_ADDRESS,
                amount=SOURCE_LDO,
            ),
            emitted_by=LDO_TOKEN,
        )
        validate_permission_revoke_event(
            event=vote_events[2],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=VOTING,
                role=web3.keccak(text=BURN_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_permission_grant_event(
            event=vote_events[3],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=VOTING,
                role=web3.keccak(text=ISSUE_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_ldo_issue_event(
            event=vote_events[4],
            i=Issue(
                token_manager_addr=TOKEN_MANAGER,
                amount=SOURCE_LDO,
            ),
            emitted_by=LDO_TOKEN,
        )
        validate_permission_revoke_event(
            event=vote_events[5],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=VOTING,
                role=web3.keccak(text=ISSUE_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_ldo_vested_event(
            event=vote_events[6],
            v=Vested(
                destination_addr=TARGET_ADDRESSES[0],
                amount=TARGET_LDOS[0],
                start=VESTING_START,
                cliff=VESTING_CLIFF,
                vesting=VESTING_TOTAL,
                revokable=IS_REVOKABLE,
            ),
            emitted_by=TOKEN_MANAGER,
        )
        validate_ldo_vested_event(
            event=vote_events[7],
            v=Vested(
                destination_addr=TARGET_ADDRESSES[1],
                amount=TARGET_LDOS[1],
                start=VESTING_START,
                cliff=VESTING_CLIFF,
                vesting=VESTING_TOTAL,
                revokable=IS_REVOKABLE,
            ),
            emitted_by=TOKEN_MANAGER,
        )
        validate_ldo_vested_event(
            event=vote_events[8],
            v=Vested(
                destination_addr=TARGET_ADDRESSES[2],
                amount=TARGET_LDOS[2],
                start=VESTING_START,
                cliff=VESTING_CLIFF,
                vesting=VESTING_TOTAL,
                revokable=IS_REVOKABLE,
            ),
            emitted_by=TOKEN_MANAGER,
        )
        validate_ldo_vested_event(
            event=vote_events[9],
            v=Vested(
                destination_addr=TARGET_ADDRESSES[3],
                amount=TARGET_LDOS[3],
                start=VESTING_START,
                cliff=VESTING_CLIFF,
                vesting=VESTING_TOTAL,
                revokable=IS_REVOKABLE,
            ),
            emitted_by=TOKEN_MANAGER,
        )
        validate_ldo_vested_event(
            event=vote_events[10],
            v=Vested(
                destination_addr=TARGET_ADDRESSES[4],
                amount=TARGET_LDOS[4],
                start=VESTING_START,
                cliff=VESTING_CLIFF,
                vesting=VESTING_TOTAL,
                revokable=IS_REVOKABLE,
            ),
            emitted_by=TOKEN_MANAGER,
        )


def move_ldo_test(stranger, ldo_token, token_manager):

    chain.snapshot()

    # cannot spend vested LDOs before vesting time
    for idx, target_address in enumerate(TARGET_ADDRESSES):
        # spend all initial LDOs non-vested (if any)
        target_address_spendable_balance = token_manager.spendableBalanceOf(target_address)
        if target_address_spendable_balance > 0:
            stranger_balance_before = ldo_token.balanceOf(stranger)
            ldo_token.transfer(stranger, target_address_spendable_balance, {"from": target_address})
            assert token_manager.spendableBalanceOf(target_address) == 0
            assert ldo_token.balanceOf(stranger) == stranger_balance_before + target_address_spendable_balance
            assert ldo_token.balanceOf(target_address) == TARGET_LDOS[idx]   

        # cannot spend vested LDOs before vesting time
        with reverts():
            ldo_token.transfer(stranger, 1, {"from": target_address})
        with reverts():
            ldo_token.transfer(stranger, TARGET_LDOS[idx], {"from": target_address})

    # sleep until cliff/total
    chain.sleep(365 * 24 * 60 * 60 - (chain.time() - VESTING_START))
    chain.mine()

    # spend vested LDOs after vesting time
    for idx, target_address in enumerate(TARGET_ADDRESSES):
        assert token_manager.spendableBalanceOf(target_address) == TARGET_LDOS[idx]
        stranger_balance_before = ldo_token.balanceOf(stranger)
        ldo_token.transfer(stranger, 1, {"from": target_address})
        ldo_token.transfer(stranger, TARGET_LDOS[idx] - 1, {"from": target_address})
        assert token_manager.spendableBalanceOf(target_address) == 0
        assert ldo_token.balanceOf(target_address) == 0
        assert ldo_token.balanceOf(stranger) == stranger_balance_before + TARGET_LDOS[idx]

    chain.revert()


def can_vote_with_vesting(ldo_holder, ldo_token, stranger, voting):

    chain.snapshot()

    old_block = web3.eth.block_number
    chain.mine(5)
    assert web3.eth.block_number == old_block + 5

    vote_items = {
        "Test vote for vesting": ("0x0000000000000000000000000000000000000000", "0x")
    }
    new_vote_id, _ = create_vote(vote_items, {"from": ldo_holder}, verbose=False)

    for target_address in TARGET_ADDRESSES:
        voting.vote(new_vote_id, True, False, {"from": target_address})
    assert voting.getVote(new_vote_id)["yea"] == sum(ldo_token.balanceOf(a) for a in TARGET_ADDRESSES)

    voting.vote(new_vote_id, True, False, {"from": ldo_holder})
    assert voting.getVote(new_vote_id)["yea"] == sum(ldo_token.balanceOf(a) for a in TARGET_ADDRESSES) + ldo_token.balanceOf(ldo_holder)

    chain.sleep(24 * 60 * 60 * 5)
    chain.mine()
    
    voting.executeVote(new_vote_id, {"from": stranger})

    chain.revert()
