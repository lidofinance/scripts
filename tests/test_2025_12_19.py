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

VESTING_MANAGER = "0xb9d7934878b5fb9610b3fe8a5e441e8fad7e293f" # TODO replace with actual address
VESTING_MANAGER_OWNER = "0xb9d7934878b5fb9610b3fe8a5e441e8fad7e293f" # TODO replace with actual address

BURN_ROLE = "BURN_ROLE"
ISSUE_ROLE = "ISSUE_ROLE"
ASSIGN_ROLE = "ASSIGN_ROLE"

LDO_TOKEN = "0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32"

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
    #vesting_contract = interface.VestingContract(VESTING_MANAGER)


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
        assert not acl.hasPermission(VESTING_MANAGER, TOKEN_MANAGER, web3.keccak(text=BURN_ROLE).hex())
        assert not acl.hasPermission(VESTING_MANAGER, TOKEN_MANAGER, web3.keccak(text=ISSUE_ROLE).hex())
        assert not acl.hasPermission(VESTING_MANAGER, TOKEN_MANAGER, web3.keccak(text=ASSIGN_ROLE).hex())

        # TODO make sure vesting_contract.vestTokens() called with correct params fails before roles are granted


        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        assert acl.hasPermission(VESTING_MANAGER, TOKEN_MANAGER, web3.keccak(text=BURN_ROLE).hex())
        assert acl.hasPermission(VESTING_MANAGER, TOKEN_MANAGER, web3.keccak(text=ISSUE_ROLE).hex())
        assert acl.hasPermission(VESTING_MANAGER, TOKEN_MANAGER, web3.keccak(text=ASSIGN_ROLE).hex())

        # TODO make sure vesting_contract.vestTokens() reverts if called by EOA (non-owner)

        #eoa = accounts[0]
        #test_vest_flow_burn_issue_assign(ldo_holder, eoa, ldo_token, vesting_contract, VESTING_MANAGER_OWNER)
        #test_cannot_vest_more_than_global_limit

        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT

        validate_permission_grant_event(
            event=vote_events[0],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=VESTING_MANAGER,
                role=web3.keccak(text=BURN_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_permission_grant_event(
            event=vote_events[1],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=VESTING_MANAGER,
                role=web3.keccak(text=ISSUE_ROLE).hex(),
            ),
            emitted_by=ACL,
        )
        validate_permission_grant_event(
            event=vote_events[2],
            p=Permission(
                app=TOKEN_MANAGER,
                entity=VESTING_MANAGER,
                role=web3.keccak(text=ASSIGN_ROLE).hex(),
            ),
            emitted_by=ACL,
        )


#def test_vest_flow_burn_issue_assign(ldo_whale, eoa, ldo_token, vesting_contract, owner):
#
#    chain.snapshot()
#
#    LDO_49M = 49_000_000 * 10**18
#
#    ldo_token.transfer(eoa, LDO_49M, {"from": ldo_whale})
#    assert ldo_token.balanceOf(eoa) == LDO_49M
#
#    tm_before = ldo_token.balanceOf(TOKEN_MANAGER)
#    supply_before = ldo_token.totalSupply()
#
#    vesting_contract.vestTokens(eoa, {"from": owner})
#
#    assert ldo_token.balanceOf(eoa) == LDO_49M
#    assert ldo_token.balanceOf(TOKEN_MANAGER) == tm_before
#    assert ldo_token.totalSupply() == supply_before
#
#    chain.revert()
#
#
#def test_cannot_vest_more_than_global_limit(ldo_whale, eoa, ldo_token, vesting_contract, owner):
#    LDO_50M = 50_000_000 * 10**18
#
#    ldo_token.transfer(eoa, LDO_50M + 1, {"from": ldo_whale})
#    assert ldo_token.balanceOf(eoa) == LDO_50M + 1
#
#    with reverts("GLOBAL_LIMIT_EXCEEDED"):
#        vesting_contract.vestTokens(eoa, {"from": owner})
#
#
#def test_global_limit_is_cumulative(ldo_whale, eoa, ldo_token, vesting_contract, owner):
#    LDO_50M = 50_000_000 * 10**18
#    
#    ldo_token.transfer(eoa, LDO_50M + 1, {"from": ldo_whale})
#    assert ldo_token.balanceOf(eoa) == LDO_50M + 1
#
#    vesting_contract.vestTokens(eoa, {"from": owner})
#    vesting_contract.vestTokens(eoa, {"from": owner})
#
#    with reverts("GLOBAL_LIMIT_EXCEEDED"):
#        vesting_contract.vestTokens(eoa, {"from": owner})
#
#def test_vesting_params_match_expected(owner, alice, ldo, vesting_forwarder, chain):
#    x = 1000 * 10**18
#    ldo.mint(alice, x, {"from": owner})
#
#    now = chain.time()
#    tx = vesting_forwarder.vestTokens(alice, {"from": owner})
#
#    # use TokenManager.getVesting
#
#    assert start == now  # if you use block timestamp as start
#    assert cliff == start + 365 * 24 * 60 * 60
#    assert vested == start + 2 * 365 * 24 * 60 * 60