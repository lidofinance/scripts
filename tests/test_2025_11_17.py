from brownie import chain, interface
from brownie.network.transaction import TransactionReceipt
import pytest

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events
)
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.allowed_recipients_registry import (
    update_spent_amount,
    set_limit_parameters,
)
from utils.agent import agent_forward


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2025_11_17 import start_vote, get_vote_items


# ============================================================================
# ============================== Constants ===================================
# ============================================================================
# TODO list all contract addresses used in tests - do not use imports from config!
# NOTE: these addresses might have a different value on other chains

VOTING = "0x2e59A20f205bB85a89C53f1936454680651E618e"
AGENT = "0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c"
EMERGENCY_PROTECTED_TIMELOCK = "0xCE0425301C85c5Ea2A0873A2dEe44d78E02D2316"
DUAL_GOVERNANCE = "0xC1db28B3301331277e307FDCfF8DE28242A4486E"
DUAL_GOVERNANCE_ADMIN_EXECUTOR = "0x23E0B465633FF5178808F4A75186E2F2F9537021"
ET_TRP_REGISTRY = "0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8"
STAKING_ROUTER = "0xFdDf38947aFB03C621C71b06C9C70bce73f12999"

# TODO Set variable to None if item is not presented
EXPECTED_VOTE_ID = 194
EXPECTED_DG_PROPOSAL_ID = 6
EXPECTED_VOTE_EVENTS_COUNT = 2
EXPECTED_DG_EVENTS_COUNT = 3
IPFS_DESCRIPTION_HASH = ""

SDVT_MODULE_ID = 2
SDVT_MODULE_NEW_TARGET_SHARE_BP = 410 # 4.1%
SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP = 444
SDVT_MODULE_MODULE_FEE_BP = 800
SDVT_MODULE_TREASURY_FEE_BP = 200
SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():

    staking_router = interface.StakingRouter(STAKING_ROUTER)

    # Create all the dual governance calls that match the voting script
    dg_items = [
        agent_forward([
            # 1.1. Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to TODO XXX
            update_spent_amount(spent_amount=0, registry_address=ET_TRP_REGISTRY),
            
            # 1.2. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to TODO XXX
            set_limit_parameters(
                limit=11_000_000 * 10**18,
                period_duration_months=12,
                registry_address=ET_TRP_REGISTRY,
            ),

            # 1.3. Increase SDVT (MODULE_ID = 2) share limit from 400 bps to 410 bps in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
            (
                staking_router.address,
                staking_router.updateStakingModule.encode_input(
                    SDVT_MODULE_ID,
                    SDVT_MODULE_NEW_TARGET_SHARE_BP,
                    SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP,
                    SDVT_MODULE_MODULE_FEE_BP,
                    SDVT_MODULE_TREASURY_FEE_BP,
                    SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK,
                    SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE,
                ),
            ),
        ])
    ]
        
    
    # Convert each dg_item to the expected format
    proposal_calls = []
    for dg_item in dg_items:
        target, data = dg_item  # agent_forward returns (target, data)
        proposal_calls.append({
            "target": target,
            "value": 0,
            "data": data
        })

    return proposal_calls


def test_vote(helpers, accounts, ldo_holder, vote_ids_from_env, stranger, dual_governance_proposal_calls):

    # =======================================================================
    # ========================= Arrange variables ===========================
    # =======================================================================
    voting = interface.Voting(VOTING)
    agent = interface.Agent(AGENT)
    timelock = interface.EmergencyProtectedTimelock(EMERGENCY_PROTECTED_TIMELOCK)
    dual_governance = interface.DualGovernance(DUAL_GOVERNANCE)


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
        # TODO add before voting checks


        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        # TODO add after voting tests


        assert len(vote_events) == EXPECTED_VOTE_EVENTS_COUNT
        assert count_vote_items_by_events(vote_tx, voting.address) == EXPECTED_VOTE_EVENTS_COUNT
        if EXPECTED_DG_PROPOSAL_ID is not None:
            assert EXPECTED_DG_PROPOSAL_ID == timelock.getProposalsCount()

            # Validate DG Proposal Submit event
            validate_dual_governance_submit_event(
                vote_events[0],
                proposal_id=EXPECTED_DG_PROPOSAL_ID,
                proposer=VOTING,
                executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                metadata="TODO DG proposal description",
                proposal_calls=dual_governance_proposal_calls,
                emitted_by=[EMERGENCY_PROTECTED_TIMELOCK, DUAL_GOVERNANCE],
            )

            # TODO validate all other voting events


    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================
            # TODO add DG before proposal executed checks


            if details["status"] == PROPOSAL_STATUS["submitted"]:
                chain.sleep(timelock.getAfterSubmitDelay() + 1)
                dual_governance.scheduleProposal(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})

            if timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)["status"] == PROPOSAL_STATUS["scheduled"]:
                chain.sleep(timelock.getAfterScheduleDelay() + 1)
                dg_tx: TransactionReceipt = timelock.execute(EXPECTED_DG_PROPOSAL_ID, {"from": stranger})
                display_dg_events(dg_tx)
                dg_events = group_dg_events_from_receipt(
                    dg_tx,
                    timelock=EMERGENCY_PROTECTED_TIMELOCK,
                    admin_executor=DUAL_GOVERNANCE_ADMIN_EXECUTOR,
                )
                assert count_vote_items_by_events(dg_tx, agent.address) == EXPECTED_DG_EVENTS_COUNT

                # TODO validate all DG events


        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================
        # TODO add DG after proposal executed checks
