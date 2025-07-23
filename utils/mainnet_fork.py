from contextlib import contextmanager
from brownie import chain, interface, accounts
from utils.config import VOTING, LDO_VOTE_EXECUTORS_FOR_TESTS, get_vote_duration
from utils.dual_governance import process_proposals
from utils.config import contracts

@contextmanager
def chain_snapshot():
    try:
        print("Making chain snapshot...")
        chain.snapshot()
        yield
    finally:
        print("Reverting the chain...")
        chain.revert()


def pass_and_exec_dao_vote(vote_id, step_by_step=False):
    dao_voting = interface.Voting(VOTING)

    if dao_voting.getVote(vote_id)["executed"]:
        print(f"[ok] Vote {vote_id} already executed")
        return

    helper_acct = accounts[0]

    if not dao_voting.canExecute(vote_id):
        print(f"Passing vote {vote_id}")

        if dao_voting.getVotePhase(vote_id) == 0:
            for holder_addr in LDO_VOTE_EXECUTORS_FOR_TESTS:
                print(f"  voting from {holder_addr}")
                helper_acct.transfer(holder_addr, "1 ether", silent=True)
                account = accounts.at(holder_addr, force=True)
                dao_voting.vote(vote_id, True, False, {"from": account, "silent": True})

        # wait for the vote to end
        time_to_end = dao_voting.getVote(vote_id)["startDate"] + get_vote_duration() - chain.time()
        if time_to_end > 0:
            chain.sleep(time_to_end)

        chain.mine()

        assert dao_voting.canExecute(vote_id)

    print(f"Executing vote {vote_id}")

    proposals_count_before = contracts.emergency_protected_timelock.getProposalsCount()
    dao_voting.executeVote(vote_id, {"from": helper_acct, "silent": True})
    assert dao_voting.getVote(vote_id)["executed"]
    print(f"[ok] Vote {vote_id} executed")

    proposals_count_after = contracts.emergency_protected_timelock.getProposalsCount()
    if proposals_count_after > proposals_count_before:
        if step_by_step:
            input("Press Enter to execute DG proposals...")
        new_proposal_ids = list(range(proposals_count_before + 1, proposals_count_after + 1))
        process_proposals(new_proposal_ids)
        print(f"[ok] DG proposals {new_proposal_ids} processed")

    if step_by_step:
        input("Press Enter to stop local node...")
