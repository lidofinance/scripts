from brownie import accounts
from utils.config import contracts
from utils.import_current_votes import start_and_execute_votes
from utils.dual_governance import process_proposals


def execute_vote(helpers, vote_ids_from_env):
    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting)
    else:
        start_and_execute_votes(contracts.voting, helpers)

# TODO revert after December Aragon
#def execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env):
#    if vote_ids_from_env and dg_proposal_ids_from_env:
#        execute_vote(helpers, vote_ids_from_env)
#        process_proposals(dg_proposal_ids_from_env)
#    elif not vote_ids_from_env and dg_proposal_ids_from_env:
#        process_proposals(dg_proposal_ids_from_env)
#    else:
#        proposals_count_before = contracts.emergency_protected_timelock.getProposalsCount()
#        execute_vote(helpers, vote_ids_from_env)
#        proposals_count_after = contracts.emergency_protected_timelock.getProposalsCount()
#        if proposals_count_after == proposals_count_before:
#            return
#        new_proposal_ids = list(range(proposals_count_before + 1, proposals_count_after + 1))
#        process_proposals(new_proposal_ids)


def execute_vote_and_process_dg_proposals(helpers, vote_ids_from_env, dg_proposal_ids_from_env):

    # V1
    proposals_count_before1 = contracts.emergency_protected_timelock.getProposalsCount()
    start_and_execute_votes(contracts.voting, helpers, 0)
    proposals_count_after1 = contracts.emergency_protected_timelock.getProposalsCount()
    new_proposal_ids1 = list(range(proposals_count_before1 + 1, proposals_count_after1 + 1))
    
    # DG1
    process_proposals(new_proposal_ids1)

    # V2
    proposals_count_before2 = contracts.emergency_protected_timelock.getProposalsCount()
    start_and_execute_votes(contracts.voting, helpers, 1)
    proposals_count_after2 = contracts.emergency_protected_timelock.getProposalsCount()
    new_proposal_ids2 = list(range(proposals_count_before2 + 1, proposals_count_after2 + 1))
    
    # DG2
    process_proposals(new_proposal_ids2)
