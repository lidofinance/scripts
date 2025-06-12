import os

from brownie import accounts
from utils.config import contracts
from utils.import_current_votes import start_and_execute_votes

from utils.test.helpers import ETH
from utils.test.oracle_report_helpers import oracle_report
from utils.test.simple_dvt_helpers import fill_simple_dvt_ops_vetted_keys
from utils.dual_governance import process_proposals


ENV_REPORT_AFTER_VOTE = "REPORT_AFTER_VOTE"
ENV_FILL_SIMPLE_DVT = "FILL_SIMPLE_DVT"


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
