from brownie import web3, interface, chain, reverts
from brownie.network.transaction import TransactionReceipt

from utils.test.tx_tracing_helpers import group_voting_events_from_receipt
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
)
from utils.test.event_validators.permission import (
    Permission,
    validate_permission_grant_event,
)


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2025_12_19 import start_vote, get_vote_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================

VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
TOKEN_MANAGER = "0xf73a1260d222f447210581DDf212D915c09a3249"
ACL = "0x9895f0f17cc1d1891b6f18ee0b483b6f221b37bb"
TRP_COMMITTEE = "0x834560F580764Bc2e0B16925F8bF229bb00cB759"

REVESTING_CONTRACT = "0xc2f50d3277539fbd54346278e7b92faa76dc7364"
DISALLOWED_CONTRACTS = [
    "0xF977814e90dA44bFA03b6295A0616a897441aceC",
    "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c",
    "0x8Fa129F87B8a11ee1ca35Abd46674F8b66984d4a",
    "0x611f7bF868a6212f871e89F7e44684045DdFB09d",
]

BURN_ROLE = "BURN_ROLE"
ISSUE_ROLE = "ISSUE_ROLE"
ASSIGN_ROLE = "ASSIGN_ROLE"

LDO_TOKEN = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"

LDO_1M = 1_000_000 * 10**18
LDO_49M = 49_000_000 * 10**18
LDO_50M = 50_000_000 * 10**18

EXPECTED_VOTE_ID = 196
EXPECTED_VOTE_EVENTS_COUNT = 3
IPFS_DESCRIPTION_HASH = "bafkreic2vwidwtcp3vx2zcz2ye2vadw245jlo26x3fhhqmcu2o34y55mgm"


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    acl = interface.ACL(ACL)
    ldo_token = interface.ERC20(LDO_TOKEN)
    revesting_contract = interface.LDORevesting(REVESTING_CONTRACT)
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
        assert not acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=BURN_ROLE).hex())
        assert not acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=ISSUE_ROLE).hex())
        assert not acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=ASSIGN_ROLE).hex())
        assert revesting_contract.owner() == TRP_COMMITTEE
        assert revesting_contract.LIFETIME() == 90 * 24 * 60 * 60  # 90 days in seconds
        assert revesting_contract.CLIFF_DURATION() == 365 * 24 * 60 * 60  # 365 days in seconds 
        assert revesting_contract.IS_REVOKABLE()
        assert revesting_contract.REVESTING_LIMIT() == 50_000_000 * 10**18  # 50 million LDO
        assert revesting_contract.VESTED_DURATION() == 365 * 24 * 60 * 60 * 2  # 2 years in seconds

        # make sure revesting with no granted roles fails
        chain.snapshot()
        ldo_token.transfer(eoa, LDO_1M, {"from": ldo_holder})
        assert ldo_token.balanceOf(eoa) == LDO_1M
        with reverts("APP_AUTH_FAILED"):
            revesting_contract.revestSpendableBalance(eoa, {"from": TRP_COMMITTEE})
        chain.revert()

        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH
        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        assert acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=BURN_ROLE).hex())
        assert acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=ISSUE_ROLE).hex())
        assert acl.hasPermission(REVESTING_CONTRACT, TOKEN_MANAGER, web3.keccak(text=ASSIGN_ROLE).hex())

        # make sure revesting called by non-owner fails
        with reverts("OwnableUnauthorizedAccount: 0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"):
            revesting_contract.revestSpendableBalance(eoa, {"from": eoa})

        revest_happy_path(ldo_holder, eoa, ldo_token, revesting_contract)
        cannot_revest_more_than_global_limit(ldo_holder, eoa, ldo_token, revesting_contract)
        cannot_revest_more_than_global_limit_cumulative(ldo_holder, eoa, ldo_token, revesting_contract)
        revest_disallowed_fails(revesting_contract)
        revest_afterlife_fails(eoa, revesting_contract)

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        validate_permission_grant_event(
            event=vote_events[0],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=REVESTING_CONTRACT,
                role=web3.keccak(text=BURN_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_permission_grant_event(
            event=vote_events[1],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=REVESTING_CONTRACT,
                role=web3.keccak(text=ISSUE_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_permission_grant_event(
            event=vote_events[2],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=REVESTING_CONTRACT,
                role=web3.keccak(text=ASSIGN_ROLE).hex(),
            ),
            emitted_by=ACL,
        )


def revest_happy_path(ldo_holder, eoa, ldo_token, revesting_contract):

    token_manager = interface.TokenManager(TOKEN_MANAGER)

    chain.snapshot()

    ldo_token.transfer(eoa, LDO_49M, {"from": ldo_holder})
    assert ldo_token.balanceOf(eoa) == LDO_49M

    tm_before = ldo_token.balanceOf(TOKEN_MANAGER)
    supply_before = ldo_token.totalSupply()
    vestings_length_before = token_manager.vestingsLengths(eoa)

    revesting_contract.revestSpendableBalance(eoa, {"from": TRP_COMMITTEE})

    assert revesting_contract.totalRevested() == LDO_49M
    assert ldo_token.balanceOf(eoa) == LDO_49M
    assert ldo_token.balanceOf(TOKEN_MANAGER) == tm_before
    assert ldo_token.totalSupply() == supply_before
    assert token_manager.vestingsLengths(eoa) == vestings_length_before + 1

    vesting = token_manager.getVesting(eoa, vestings_length_before)
    assert vesting["amount"] == LDO_49M
    assert vesting["start"] >= chain.time() - 60 and vesting["start"] <= chain.time()  # allow up to 1 minute time difference because of Hardhat time issues
    assert vesting["cliff"] == vesting["start"] + 365 * 24 * 60 * 60
    assert vesting["vesting"] == vesting["start"] + 365 * 24 * 60 * 60 * 2
    assert vesting["revokable"]

    assert token_manager.spendableBalanceOf(eoa) == 0
    chain.sleep(365 * 24 * 60 * 60)  # sleep for 1 year
    chain.mine()
    assert token_manager.spendableBalanceOf(eoa) == LDO_49M // 2
    chain.sleep(365 * 24 * 60 * 60 // 2)  # sleep for 0.5 year
    chain.mine()
    assert token_manager.spendableBalanceOf(eoa) == LDO_49M * 3 // 4
    chain.sleep(365 * 24 * 60 * 60 // 2)  # sleep for 0.5 year
    chain.mine()
    assert token_manager.spendableBalanceOf(eoa) == LDO_49M

    chain.revert()


def cannot_revest_more_than_global_limit(ldo_holder, eoa, ldo_token, revesting_contract):

    token_manager = interface.TokenManager(TOKEN_MANAGER)
    
    chain.snapshot()

    ldo_token.transfer(eoa, LDO_50M + 1, {"from": ldo_holder})
    assert ldo_token.balanceOf(eoa) == LDO_50M + 1

    tm_before = ldo_token.balanceOf(TOKEN_MANAGER)
    supply_before = ldo_token.totalSupply()
    vestings_length_before = token_manager.vestingsLengths(eoa)

    revesting_contract.revestSpendableBalance(eoa, {"from": TRP_COMMITTEE})

    assert revesting_contract.totalRevested() == LDO_50M
    assert ldo_token.balanceOf(eoa) == LDO_50M + 1
    assert ldo_token.balanceOf(TOKEN_MANAGER) == tm_before
    assert ldo_token.totalSupply() == supply_before
    assert token_manager.vestingsLengths(eoa) == vestings_length_before + 1

    vesting = token_manager.getVesting(eoa, vestings_length_before)
    assert vesting["amount"] == LDO_50M
    assert vesting["start"] >= chain.time() - 60 and vesting["start"] <= chain.time()  # allow up to 1 minute time difference because of Hardhat time issues
    assert vesting["cliff"] == vesting["start"] + 365 * 24 * 60 * 60
    assert vesting["vesting"] == vesting["start"] + 365 * 24 * 60 * 60 * 2
    assert vesting["revokable"]

    chain.revert()


def cannot_revest_more_than_global_limit_cumulative(ldo_holder, eoa, ldo_token, revesting_contract):
    
    token_manager = interface.TokenManager(TOKEN_MANAGER)
    
    chain.snapshot()

    ldo_token.transfer(eoa, LDO_49M, {"from": ldo_holder})
    assert ldo_token.balanceOf(eoa) == LDO_49M

    tm_before = ldo_token.balanceOf(TOKEN_MANAGER)
    supply_before = ldo_token.totalSupply()
    vestings_length_before = token_manager.vestingsLengths(eoa)

    revesting_contract.revestSpendableBalance(eoa, {"from": TRP_COMMITTEE})

    assert revesting_contract.totalRevested() == LDO_49M
    assert ldo_token.balanceOf(eoa) == LDO_49M
    assert ldo_token.balanceOf(TOKEN_MANAGER) == tm_before
    assert ldo_token.totalSupply() == supply_before
    assert token_manager.vestingsLengths(eoa) == vestings_length_before + 1

    vesting = token_manager.getVesting(eoa, vestings_length_before)
    assert vesting["amount"] == LDO_49M
    assert vesting["start"] >= chain.time() - 60 and vesting["start"] <= chain.time()  # allow up to 1 minute time difference because of Hardhat time issues
    assert vesting["cliff"] == vesting["start"] + 365 * 24 * 60 * 60
    assert vesting["vesting"] == vesting["start"] + 365 * 24 * 60 * 60 * 2
    assert vesting["revokable"]


    ldo_token.transfer(eoa, LDO_1M + 1, {"from": ldo_holder})
    assert ldo_token.balanceOf(eoa) == LDO_49M + LDO_1M + 1

    revesting_contract.revestSpendableBalance(eoa, {"from": TRP_COMMITTEE})

    assert revesting_contract.totalRevested() == LDO_50M
    assert ldo_token.balanceOf(eoa) == LDO_49M + LDO_1M + 1
    assert ldo_token.balanceOf(TOKEN_MANAGER) == tm_before
    assert ldo_token.totalSupply() == supply_before
    assert token_manager.vestingsLengths(eoa) == vestings_length_before + 2

    vesting = token_manager.getVesting(eoa, vestings_length_before+1)
    assert vesting["amount"] == LDO_1M
    assert vesting["start"] >= chain.time() - 60 and vesting["start"] <= chain.time()  # allow up to 1 minute time difference because of Hardhat time issues
    assert vesting["cliff"] == vesting["start"] + 365 * 24 * 60 * 60
    assert vesting["vesting"] == vesting["start"] + 365 * 24 * 60 * 60 * 2
    assert vesting["revokable"]

    chain.revert()

def revest_disallowed_fails(revesting_contract):

    chain.snapshot()
    
    for disallowed in DISALLOWED_CONTRACTS:
        with reverts(f"AccountDisallowed: {disallowed.lower()}"):
            revesting_contract.revestSpendableBalance(disallowed, {"from": TRP_COMMITTEE})

    chain.revert()


def revest_afterlife_fails(eoa, revesting_contract):

    chain.snapshot()

    assert not revesting_contract.isExpired()

    chain.sleep(revesting_contract.LIFETIME() + 1)
    chain.mine()

    assert revesting_contract.isExpired()

    with reverts("Expired: "):
        revesting_contract.revestSpendableBalance(eoa, {"from": TRP_COMMITTEE})

    chain.revert()