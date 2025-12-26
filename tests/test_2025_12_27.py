from brownie import web3, interface, chain, reverts
from brownie.network.transaction import TransactionReceipt

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
    validate_permission_revoke_event,
)
from utils.test.event_validators.token_manager import (
    Vested,
    VestedRevoke,
    validate_ldo_revoke_vested_event,
    validate_ldo_vested_event,
)


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2025_12_27 import start_vote, get_vote_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================

AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
TOKEN_MANAGER = "0xf73a1260d222f447210581DDf212D915c09a3249"
ACL = "0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb"
REVESTING_CONTRACT = "0xc2f50d3277539fbd54346278e7b92faa76dc7364"
TRP_COMMITTEE = "0x834560F580764Bc2e0B16925F8bF229bb00cB759"

SOURCE_ADDRESS = "0xa8107de483f9623390d543b77c8e4bbb6f7af752"
SOURCE_ADDRESS_VESTING_ID = 0
SOURCE_LDO = 48_934_690_0011 * 10**14  # 48,934,690.0011 LDO

TARGET_ADDRESSES = [
    "0xED3D9bAC1B26610A6f8C42F4Fd2c741a16647056",
    "0x7bd77405a7c28F50a1010e2185297A25165FD5C6",
    "0x7E363142293cc25F96F94d5621ea01bCCe2890E8",
    "0xECE4e341EbcC2B57c40FCf74f47bc61DfDC87fe2",
    "0x7F514FC631Cca86303e20575592143DD2E253175",
    "0xdCdeC1fce45e76fE82E036344DE19061d1f0aA31",
    "0x3d56d86a60b92132b37f226EA5A23F84C805Ce29",
    "0x28562FBe6d078d2526A0A8d1489245fF74fcA7eB",
    "0xf930e6d88ecd10788361517fc45C986c0a1b10e5",
    "0x00E78b7770D8a41A0f37f2d206e65f9Cd391cf0a",
]
TARGET_LDOS = [
    10_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    5_000_000 * 10**18,
    2_000_000 * 10**18,
    1_934_690_0011 * 10**14,
]

VESTING_START = 1767225600 # Thu Jan 01 2026 00:00:00 GMT+0000
VESTING_CLIFF = 1798761600 # Fri Jan 01 2027 00:00:00 GMT+0000
VESTING_TOTAL = VESTING_CLIFF
IS_REVOKABLE = True

BURN_ROLE = "BURN_ROLE"
ISSUE_ROLE = "ISSUE_ROLE"
ASSIGN_ROLE = "ASSIGN_ROLE"

LDO_TOKEN = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"

EXPECTED_VOTE_ID = 197
EXPECTED_VOTE_EVENTS_COUNT = 14
IPFS_DESCRIPTION_HASH = "bafkreihistgxpm5srj3t3qr5tj5k5pyehf4ddnwswzrzfexu65ecvakjry"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    acl = interface.ACL(ACL)
    ldo_token = interface.ERC20(LDO_TOKEN)
    token_manager = interface.TokenManager(TOKEN_MANAGER)
    eoa = accounts[0]


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

        # Items 1
        assert token_manager.vestingsLengths(SOURCE_ADDRESS) == 1
        assert token_manager.getVesting(SOURCE_ADDRESS, SOURCE_ADDRESS_VESTING_ID)["amount"] == SOURCE_LDO
        assert ldo_token.balanceOf(SOURCE_ADDRESS) == SOURCE_LDO
        assert ldo_token.totalSupply() == 1_000_000_000 * 10**18
        assert ldo_token.balanceOf(TOKEN_MANAGER) == 0
        agent_ldo_balance_before = ldo_token.balanceOf(AGENT)

        # Items 2-11
        for target_address in TARGET_ADDRESSES:
            assert ldo_token.balanceOf(target_address) == 0
            assert token_manager.vestingsLengths(target_address) == 0
            assert token_manager.spendableBalanceOf(target_address) == 0
            assert accounts.at(target_address, force=True).nonce == 1

        # Items 12-14
        assert acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=ISSUE_ROLE).hex())
        assert acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=BURN_ROLE).hex())
        assert acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=ASSIGN_ROLE).hex())


        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH
        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        # Items 1
        assert token_manager.vestingsLengths(SOURCE_ADDRESS) == 1
        assert token_manager.getVesting(SOURCE_ADDRESS, SOURCE_ADDRESS_VESTING_ID)["amount"] == 0
        assert ldo_token.balanceOf(SOURCE_ADDRESS) == 0
        assert ldo_token.totalSupply() == 1_000_000_000 * 10**18
        assert ldo_token.balanceOf(TOKEN_MANAGER) == 0
        assert ldo_token.balanceOf(AGENT) == agent_ldo_balance_before

        # Items 2-11
        for idx, target_address in enumerate(TARGET_ADDRESSES):
            assert ldo_token.balanceOf(target_address) == TARGET_LDOS[idx]
            assert token_manager.vestingsLengths(target_address) == 1
            assert token_manager.spendableBalanceOf(target_address) == 0
            assert accounts.at(target_address, force=True).nonce == 1
            vesting = token_manager.getVesting(target_address, token_manager.vestingsLengths(target_address) - 1)
            assert vesting["amount"] == TARGET_LDOS[idx]
            assert vesting["start"] == VESTING_START
            assert vesting["cliff"] == VESTING_CLIFF
            assert vesting["vesting"] == VESTING_TOTAL
            assert vesting["revokable"] == IS_REVOKABLE

        # Items 12-14
        assert not acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=ISSUE_ROLE).hex())
        assert not acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=BURN_ROLE).hex())
        assert not acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=ASSIGN_ROLE).hex())

        # scenario tests
        move_ldo_test(eoa, ldo_token, token_manager)
        can_vote_with_vesting(ldo_holder, ldo_token, eoa, voting)
        # make sure revesting with no granted roles fails
        chain.snapshot()
        ldo_token.transfer(eoa, 100_000 * 10**18, {"from": ldo_holder})
        assert ldo_token.balanceOf(eoa) == 100_000 * 10**18
        with reverts("APP_AUTH_FAILED"):
            interface.LDORevesting(REVESTING_CONTRACT).revestSpendableBalance(eoa, {"from": TRP_COMMITTEE})
        chain.revert()


        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        validate_ldo_revoke_vested_event(
            event=vote_events[0],
            v=VestedRevoke(
                revoke_from=SOURCE_ADDRESS,
                vesting_id=SOURCE_ADDRESS_VESTING_ID,
                amount=SOURCE_LDO,
            ),
            emitted_by=TOKEN_MANAGER,
        )
        validate_ldo_vested_event(
            event=vote_events[1],
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
            event=vote_events[2],
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
            event=vote_events[3],
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
            event=vote_events[4],
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
            event=vote_events[5],
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
        validate_ldo_vested_event(
            event=vote_events[6],
            v=Vested(
                destination_addr=TARGET_ADDRESSES[5],
                amount=TARGET_LDOS[5],
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
                destination_addr=TARGET_ADDRESSES[6],
                amount=TARGET_LDOS[6],
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
                destination_addr=TARGET_ADDRESSES[7],
                amount=TARGET_LDOS[7],
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
                destination_addr=TARGET_ADDRESSES[8],
                amount=TARGET_LDOS[8],
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
                destination_addr=TARGET_ADDRESSES[9],
                amount=TARGET_LDOS[9],
                start=VESTING_START,
                cliff=VESTING_CLIFF,
                vesting=VESTING_TOTAL,
                revokable=IS_REVOKABLE,
            ),
            emitted_by=TOKEN_MANAGER,
        )
        validate_permission_revoke_event(
            event=vote_events[11],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=REVESTING_CONTRACT,
                role=web3.keccak(text=BURN_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_permission_revoke_event(
            event=vote_events[12],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=REVESTING_CONTRACT,
                role=web3.keccak(text=ISSUE_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_permission_revoke_event(
            event=vote_events[13],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=REVESTING_CONTRACT,
                role=web3.keccak(text=ASSIGN_ROLE).hex(),
            ),
            emitted_by=ACL,
        )


def move_ldo_test(eoa, ldo_token, token_manager):

    chain.snapshot()

    # cannot spend vested LDOs before vesting time
    for idx, target_address in enumerate(TARGET_ADDRESSES):
        # spend all initial LDOs non-vested (if any)
        target_address_spendable_balance = token_manager.spendableBalanceOf(target_address)
        if target_address_spendable_balance > 0:
            eoa_balance_before = ldo_token.balanceOf(eoa)
            ldo_token.transfer(eoa, target_address_spendable_balance, {"from": target_address})
            assert token_manager.spendableBalanceOf(target_address) == 0
            assert ldo_token.balanceOf(eoa) == eoa_balance_before + target_address_spendable_balance
            assert ldo_token.balanceOf(target_address) == TARGET_LDOS[idx]   

        # cannot spend vested LDOs before vesting time
        with reverts():
            ldo_token.transfer(eoa, 1, {"from": target_address})
        with reverts():
            ldo_token.transfer(eoa, TARGET_LDOS[idx], {"from": target_address})

    # sleep until cliff/total
    time_to_cliff = VESTING_CLIFF - chain.time()
    if time_to_cliff > 0:
        chain.sleep(time_to_cliff)
        chain.mine()

    # spend vested LDOs after vesting time
    for idx, target_address in enumerate(TARGET_ADDRESSES):
        assert token_manager.spendableBalanceOf(target_address) == TARGET_LDOS[idx]
        eoa_balance_before = ldo_token.balanceOf(eoa)
        ldo_token.transfer(eoa, 1, {"from": target_address})
        ldo_token.transfer(eoa, TARGET_LDOS[idx] - 1, {"from": target_address})
        assert token_manager.spendableBalanceOf(target_address) == 0
        assert ldo_token.balanceOf(target_address) == 0
        assert ldo_token.balanceOf(eoa) == eoa_balance_before + TARGET_LDOS[idx]

    chain.revert()


def can_vote_with_vesting(ldo_holder, ldo_token, eoa, voting):

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
    
    voting.executeVote(new_vote_id, {"from": eoa})

    chain.revert()
