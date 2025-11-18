from brownie import chain, interface, reverts, accounts
from brownie.network.transaction import TransactionReceipt
import pytest

from utils.test.tx_tracing_helpers import (
    group_voting_events_from_receipt,
    group_dg_events_from_receipt,
    count_vote_items_by_events,
    display_voting_events,
    display_dg_events
)
from utils.test.easy_track_helpers import create_and_enact_payment_motion
from utils.test.event_validators.staking_router import validate_staking_module_update_event, StakingModuleItem
from utils.evm_script import encode_call_script
from utils.voting import find_metadata_by_vote_id
from utils.ipfs import get_lido_vote_cid_from_str
from utils.dual_governance import PROPOSAL_STATUS
from utils.test.event_validators.dual_governance import validate_dual_governance_submit_event
from utils.allowed_recipients_registry import (
    unsafe_set_spent_amount,
    set_limit_parameters,
)
from utils.agent import agent_forward
from utils.test.event_validators.payout import (
    validate_token_payout_event,
    Payout,
)
from utils.test.event_validators.allowed_recipients_registry import (
    validate_set_limit_parameter_event,
    validate_set_spent_amount_event,
)


# ============================================================================
# ============================== Import vote =================================
# ============================================================================
from scripts.vote_2025_11_24 import start_vote, get_vote_items


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
LOL_MS = "0x87D93d9B2C672bf9c9642d853a8682546a5012B5"
DEV_GAS_STORE = "0x7FEa69d107A77B5817379d1254cc80D9671E171b"
ET_EVM_SCRIPT_EXECUTOR = "0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
DEPOSIT_SECURITY_MODULE = "0xffa96d84def2ea035c7ab153d8b991128e3d72fd"
LIDO = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
SDVT = "0xaE7B191A31f627b4eB1d4DaC64eaB9976995b433"
EASY_TRACK = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"
TRP_COMMITTEE = "0x834560F580764Bc2e0B16925F8bF229bb00cB759"
TRP_TOP_UP_EVM_SCRIPT_FACTORY = "0xBd2b6dC189EefD51B273F5cb2d99BA1ce565fb8C"
LDO_TOKEN = "0x5a98fcbea516cf06857215779fd812ca3bef1b32"

# TODO Set variable to None if item is not presented
EXPECTED_VOTE_ID = 194
EXPECTED_DG_PROPOSAL_ID = 6
EXPECTED_VOTE_EVENTS_COUNT = 2
EXPECTED_DG_EVENTS_COUNT = 3
IPFS_DESCRIPTION_HASH = "bafkreigs2dewxxu7rj6eifpxsqvib23nsiw2ywsmh3lhewyqlmyn46obnm"

SDVT_MODULE_ID = 2
SDVT_MODULE_OLD_TARGET_SHARE_BP = 400
SDVT_MODULE_NEW_TARGET_SHARE_BP = 430
SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP = 444
SDVT_MODULE_MODULE_FEE_BP = 800
SDVT_MODULE_TREASURY_FEE_BP = 200
SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK = 150
SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE = 25
SDVT_MODULE_NAME = "SimpleDVT"

MATIC_TOKEN = "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0"
MATIC_IN_TREASURY_BEFORE = 508_106_165_781_175_837_137_177
MATIC_IN_TREASURY_AFTER = 165_781_175_837_137_177
MATIC_IN_LIDO_LABS_BEFORE = 0
MATIC_IN_LIDO_LABS_AFTER = 508_106 * 10**18

TRP_LIMIT_BEFORE = 9_178_284.42 * 10**18
TRP_ALREADY_SPENT_BEFORE = 2_708_709 * 10**18
TRP_ALREADY_SPENT_AFTER = 0
TRP_LIMIT_AFTER = 15_000_000 * 10**18
TRP_PERIOD_START_TIMESTAMP = 1735689600  # January 1, 2025 UTC
TRP_PERIOD_END_TIMESTAMP = 1767225600  # January 1, 2026 UTC
TRP_PERIOD_DURATION_MONTHS = 12


@pytest.fixture(scope="module")
def dual_governance_proposal_calls():

    staking_router = interface.StakingRouter(STAKING_ROUTER)

    # Create all the dual governance calls that match the voting script
    dg_items = [
        agent_forward([
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
        ]),
        agent_forward([
            unsafe_set_spent_amount(spent_amount=0, registry_address=ET_TRP_REGISTRY),
        ]),
        agent_forward([
            set_limit_parameters(
                limit=TRP_LIMIT_AFTER,
                period_duration_months=TRP_PERIOD_DURATION_MONTHS,
                registry_address=ET_TRP_REGISTRY,
            ),
        ]),
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
    matic_token = interface.ERC20(MATIC_TOKEN)
    staking_router = interface.StakingRouter(STAKING_ROUTER)
    et_trp_registry = interface.AllowedRecipientRegistry(ET_TRP_REGISTRY)


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

        # 2. Transfer 508,106 MATIC 0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Liquidity Observation Lab (LOL) Multisig 0x87D93d9B2C672bf9c9642d853a8682546a5012B5
        matic_treasury_balance_before = matic_token.balanceOf(agent.address)
        assert matic_treasury_balance_before == MATIC_IN_TREASURY_BEFORE
        matic_labs_balance_before = matic_token.balanceOf(LOL_MS)
        assert matic_labs_balance_before == MATIC_IN_LIDO_LABS_BEFORE


        assert get_lido_vote_cid_from_str(find_metadata_by_vote_id(vote_id)) == IPFS_DESCRIPTION_HASH

        vote_tx: TransactionReceipt = helpers.execute_vote(vote_id=vote_id, accounts=accounts, dao_voting=voting)
        display_voting_events(vote_tx)
        vote_events = group_voting_events_from_receipt(vote_tx)


        # =======================================================================
        # ========================= After voting checks =========================
        # =======================================================================
        # TODO add after voting tests

        # 2. Transfer 508,106 MATIC 0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0 from Aragon Agent 0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c to Liquidity Observation Lab (LOL) Multisig 0x87D93d9B2C672bf9c9642d853a8682546a5012B5
        matic_treasury_balance_after = matic_token.balanceOf(agent.address)
        assert matic_treasury_balance_after == MATIC_IN_TREASURY_AFTER
        matic_labs_balance_after = matic_token.balanceOf(LOL_MS)
        assert matic_labs_balance_after == MATIC_IN_LIDO_LABS_AFTER
        # make sure LOL can actually spend the received MATIC
        matic_token.transfer(DEV_GAS_STORE, MATIC_IN_LIDO_LABS_AFTER / 2, {"from": LOL_MS})
        assert matic_token.balanceOf(LOL_MS) == MATIC_IN_LIDO_LABS_AFTER / 2
        assert matic_token.balanceOf(DEV_GAS_STORE) == MATIC_IN_LIDO_LABS_AFTER / 2

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
                metadata="Upgrade Lido Protocol to V3, raise SDVT stake share limit and reset Easy Track TRP limit",
                proposal_calls=dual_governance_proposal_calls,
            )

            # TODO validate all other voting events

            validate_token_payout_event(
                event=vote_events[1],
                p=Payout(
                    token_addr=MATIC_TOKEN,
                    from_addr=AGENT,
                    to_addr=LOL_MS,
                    amount=MATIC_IN_LIDO_LABS_AFTER),
                is_steth=False,
                emitted_by=AGENT
            )


    if EXPECTED_DG_PROPOSAL_ID is not None:
        details = timelock.getProposalDetails(EXPECTED_DG_PROPOSAL_ID)
        if details["status"] != PROPOSAL_STATUS["executed"]:
            # =========================================================================
            # ================== DG before proposal executed checks ===================
            # =========================================================================
            # TODO add DG before proposal executed checks

            # 1.1. Raise SDVT (MODULE_ID = 2) stake share limit from 400 bps to 430 bps in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
            sdvt_module_before = staking_router.getStakingModule(SDVT_MODULE_ID)
            assert sdvt_module_before['stakeShareLimit'] == SDVT_MODULE_OLD_TARGET_SHARE_BP
            assert sdvt_module_before['id'] == SDVT_MODULE_ID
            assert sdvt_module_before['priorityExitShareThreshold'] == SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP
            assert sdvt_module_before['stakingModuleFee'] == SDVT_MODULE_MODULE_FEE_BP
            assert sdvt_module_before['treasuryFee'] == SDVT_MODULE_TREASURY_FEE_BP
            assert sdvt_module_before['maxDepositsPerBlock'] == SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK
            assert sdvt_module_before['minDepositBlockDistance'] == SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE
            assert sdvt_module_before['name'] == SDVT_MODULE_NAME

            # 1.2. Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0 LDO
            # 1.3. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 15'000'000 LDO with unchanged period duration of 12 months
            trp_limit_before, trp_period_duration_months_before = et_trp_registry.getLimitParameters()
            trp_already_spent_amount_before, trp_spendable_balance_before, trp_period_start_before, trp_period_end_before = et_trp_registry.getPeriodState()
            assert trp_limit_before == TRP_LIMIT_BEFORE
            assert trp_period_duration_months_before == TRP_PERIOD_DURATION_MONTHS
            assert trp_already_spent_amount_before == TRP_ALREADY_SPENT_BEFORE
            assert trp_spendable_balance_before == TRP_LIMIT_BEFORE - TRP_ALREADY_SPENT_BEFORE
            assert trp_period_start_before == TRP_PERIOD_START_TIMESTAMP
            assert trp_period_end_before == TRP_PERIOD_END_TIMESTAMP


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
                assert len(dg_events) == EXPECTED_DG_EVENTS_COUNT

                # TODO validate all DG events

                validate_staking_module_update_event(
                    event=dg_events[0],
                    module_item=StakingModuleItem(
                        id=SDVT_MODULE_ID,
                        name=SDVT_MODULE_NAME,
                        address=None,
                        target_share=SDVT_MODULE_NEW_TARGET_SHARE_BP,
                        module_fee=SDVT_MODULE_MODULE_FEE_BP,
                        treasury_fee=SDVT_MODULE_TREASURY_FEE_BP,
                        priority_exit_share=SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP),
                    emitted_by=STAKING_ROUTER
                )

                validate_set_spent_amount_event(
                    dg_events[1],
                    new_spent_amount=0,
                    emitted_by=ET_TRP_REGISTRY,
                )

                validate_set_limit_parameter_event(
                    dg_events[2],
                    limit=TRP_LIMIT_AFTER,
                    period_duration_month=TRP_PERIOD_DURATION_MONTHS,
                    period_start_timestamp=TRP_PERIOD_START_TIMESTAMP,
                    emitted_by=ET_TRP_REGISTRY,
                )

        # =========================================================================
        # ==================== After DG proposal executed checks ==================
        # =========================================================================
        # TODO add DG after proposal executed checks

        # 1.1. Raise SDVT (MODULE_ID = 2) stake share limit from 400 bps to 430 bps in Staking Router 0xFdDf38947aFB03C621C71b06C9C70bce73f12999
        sdvt_module_after = staking_router.getStakingModule(SDVT_MODULE_ID)
        assert sdvt_module_after['stakeShareLimit'] == SDVT_MODULE_NEW_TARGET_SHARE_BP
        assert sdvt_module_after['id'] == SDVT_MODULE_ID
        assert sdvt_module_after['priorityExitShareThreshold'] == SDVT_MODULE_PRIORITY_EXIT_THRESHOLD_BP
        assert sdvt_module_after['stakingModuleFee'] == SDVT_MODULE_MODULE_FEE_BP
        assert sdvt_module_after['treasuryFee'] == SDVT_MODULE_TREASURY_FEE_BP
        assert sdvt_module_after['maxDepositsPerBlock'] == SDVT_MODULE_MAX_DEPOSITS_PER_BLOCK
        assert sdvt_module_after['minDepositBlockDistance'] == SDVT_MODULE_MIN_DEPOSIT_BLOCK_DISTANCE
        assert sdvt_module_after['name'] == SDVT_MODULE_NAME
        # additional checks to make sure no other fields were changed
        assert sdvt_module_after['id'] == sdvt_module_before['id']
        assert sdvt_module_after['stakingModuleAddress'] == sdvt_module_before['stakingModuleAddress']
        assert sdvt_module_after['stakingModuleFee'] == sdvt_module_before['stakingModuleFee']
        assert sdvt_module_after['treasuryFee'] == sdvt_module_before['treasuryFee']
        assert sdvt_module_after['status'] == sdvt_module_before['status']
        assert sdvt_module_after['name'] == sdvt_module_before['name']
        assert sdvt_module_after['lastDepositAt'] == sdvt_module_before['lastDepositAt']
        assert sdvt_module_after['lastDepositBlock'] == sdvt_module_before['lastDepositBlock']
        assert sdvt_module_after['exitedValidatorsCount'] == sdvt_module_before['exitedValidatorsCount']
        assert sdvt_module_after['maxDepositsPerBlock'] == sdvt_module_before['maxDepositsPerBlock']
        assert sdvt_module_after['minDepositBlockDistance'] == sdvt_module_before['minDepositBlockDistance']
        assert sdvt_module_after['priorityExitShareThreshold'] == sdvt_module_before['priorityExitShareThreshold']
        assert len(sdvt_module_after.items()) == len(sdvt_module_before.items())
        assert len(sdvt_module_after.items()) == 13

        # 1.2. Set spent amount for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 0 LDO
        # 1.3. Set limit for Easy Track TRP registry 0x231Ac69A1A37649C6B06a71Ab32DdD92158C80b8 to 15'000'000 LDO with unchanged period duration of 12 months
        trp_limit_after, trp_period_duration_months_after = et_trp_registry.getLimitParameters()
        trp_already_spent_amount_after, trp_spendable_balance_after, trp_period_start_after, trp_period_end_after = et_trp_registry.getPeriodState()
        assert trp_limit_after == TRP_LIMIT_AFTER
        assert trp_period_duration_months_after == TRP_PERIOD_DURATION_MONTHS
        assert trp_already_spent_amount_after == TRP_ALREADY_SPENT_AFTER
        assert trp_spendable_balance_after == TRP_LIMIT_AFTER - TRP_ALREADY_SPENT_AFTER
        assert trp_period_start_after == TRP_PERIOD_START_TIMESTAMP
        assert trp_period_end_after == TRP_PERIOD_END_TIMESTAMP

        # additional test for TRP ET factory behavior after the vote
        trp_limit_test(stranger)


def trp_limit_test(stranger):

    easy_track = interface.EasyTrack(EASY_TRACK)
    ldo_token = interface.ERC20(LDO_TOKEN)
    to_spend = TRP_LIMIT_AFTER - TRP_ALREADY_SPENT_AFTER
    max_spend_at_once = 5_000_000 * 10**18
    trp_committee_account = accounts.at(TRP_COMMITTEE, force=True)

    chain.snapshot()

    # check that there is no way to spend more then expected
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            TRP_COMMITTEE,
            TRP_TOP_UP_EVM_SCRIPT_FACTORY,
            ldo_token,
            [trp_committee_account],
            [to_spend + 1],
            stranger,
        )
    
    # spend all step by step
    while to_spend > 0:
        create_and_enact_payment_motion(
            easy_track,
            TRP_COMMITTEE,
            TRP_TOP_UP_EVM_SCRIPT_FACTORY,
            ldo_token,
            [trp_committee_account],
            [min(max_spend_at_once, to_spend)],
            stranger,
        )
        to_spend -= min(max_spend_at_once, to_spend)

    # make sure there is nothing left so that you can't spend anymore
    with reverts("SUM_EXCEEDS_SPENDABLE_BALANCE"):
        create_and_enact_payment_motion(
            easy_track,
            TRP_COMMITTEE,
            TRP_TOP_UP_EVM_SCRIPT_FACTORY,
            ldo_token,
            [trp_committee_account],
            [1],
            stranger,
        )

    chain.revert()
