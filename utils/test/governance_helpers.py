import os

from brownie import chain, accounts
from utils.config import contracts
from utils.import_current_votes import start_and_execute_votes

from utils.test.helpers import ETH
from utils.test.oracle_report_helpers import oracle_report
from utils.test.simple_dvt_helpers import fill_simple_dvt_ops_vetted_keys


ENV_REPORT_AFTER_VOTE = "REPORT_AFTER_VOTE"
ENV_FILL_SIMPLE_DVT = "FILL_SIMPLE_DVT"

# https://github.com/lidofinance/dual-governance/blob/main/contracts/libraries/ExecutableProposals.sol#L27
PROPOSAL_STATUS = {
    "not_exist": 0,
    "submitted": 1,
    "scheduled": 2,
    "executed": 3,
    "cancelled": 4,
}

# https://github.com/lidofinance/dual-governance/blob/main/contracts/libraries/DualGovernanceStateMachine.sol#L35
DUAL_GOVERNANCE_STATE = {
    "normal": 1,
    "veto_signalling": 2,
    "veto_signalling_deactivation": 3,
    "veto_cooldown": 4,
    "rage_quit": 5,
}


def execute_vote(helpers, vote_ids_from_env, stranger):
    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting)
    else:
        start_and_execute_votes(contracts.voting, helpers)

    if os.getenv(ENV_FILL_SIMPLE_DVT):
        print(f"Prefilling SimpleDVT...")
        fill_simple_dvt_ops_vetted_keys(stranger)

    if os.getenv(ENV_REPORT_AFTER_VOTE):
        oracle_report(cl_diff=ETH(523), exclude_vaults_balances=False)
    

def execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, proposal_ids_from_env, stranger):    
    if proposal_ids_from_env:
        new_proposal_ids = proposal_ids_from_env
    else:
        proposals_count_before = contracts.emergency_protected_timelock.getProposalsCount()
        execute_vote(helpers, vote_ids_from_env, stranger)
        proposals_count_after = contracts.emergency_protected_timelock.getProposalsCount()
        if proposals_count_after == proposals_count_before:
            return
        new_proposal_ids = list(range(proposals_count_before + 1, proposals_count_after + 1))
    process_proposals(new_proposal_ids)


def process_proposals(proposal_ids):
    executor = accounts[0]

    after_submit_delay = contracts.emergency_protected_timelock.getAfterSubmitDelay()
    after_schedule_delay = contracts.emergency_protected_timelock.getAfterScheduleDelay()

    submitted_proposals = []
    scheduled_proposals = []

    for proposal_id in proposal_ids:
        (_, _, _, _, proposal_status) = contracts.emergency_protected_timelock.getProposalDetails(proposal_id)
        if proposal_status == PROPOSAL_STATUS["submitted"]:
            submitted_proposals.append(proposal_id)
        elif proposal_status == PROPOSAL_STATUS["scheduled"]:
            scheduled_proposals.append(proposal_id)

    if len(submitted_proposals):
        chain.sleep(after_submit_delay + 1)

        first_proposal_id = submitted_proposals[0]
        while not contracts.dual_governance.canScheduleProposal(first_proposal_id):
            wait_for_normal_state(executor)

        for proposal_id in submitted_proposals:
            contracts.dual_governance.scheduleProposal(proposal_id, {"from": executor})
            scheduled_proposals.append(proposal_id)

    if len(scheduled_proposals):
        chain.sleep(after_schedule_delay + 1)

        for proposal_id in scheduled_proposals:
            contracts.emergency_protected_timelock.execute(proposal_id, {"from": executor})
            (_, _, _, _, proposal_status) = contracts.emergency_protected_timelock.getProposalDetails(proposal_id)
            assert proposal_status == PROPOSAL_STATUS["executed"], f"Proposal {proposal_id} execution failed"


def wait_for_normal_state(executor):
    # https://github.com/lidofinance/dual-governance/blob/main/contracts/interfaces/IDualGovernance.sol#L15
    state_details = contracts.dual_governance.getStateDetails()

    effective_state = state_details[0]
    persisted_state_entered_at = state_details[2]
    veto_signalling_activated_at = state_details[3]
    veto_signalling_duration = state_details[7]

    if effective_state == DUAL_GOVERNANCE_STATE["veto_signalling"]:
        remaining_time = veto_signalling_activated_at + veto_signalling_duration - chain.time()
        if remaining_time > 0:
            chain.sleep(remaining_time + 1)

    if effective_state == DUAL_GOVERNANCE_STATE["veto_signalling_deactivation"]:
        # https://github.com/lidofinance/dual-governance/blob/main/contracts/ImmutableDualGovernanceConfigProvider.sol#L98
        config = contracts.dual_governance_config_provider.getDualGovernanceConfig()
        veto_signalling_deactivation_max_duration = config[4]

        remaining_time = persisted_state_entered_at + veto_signalling_deactivation_max_duration - chain.time()

        if remaining_time > 0:
            chain.sleep(remaining_time + 1)
        
    contracts.dual_governance.activateNextState({"from": executor})
