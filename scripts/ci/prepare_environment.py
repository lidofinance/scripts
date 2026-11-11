import os

from typing import Callable, Tuple, List

from tests.conftest import Helpers, get_active_proposals_from_env

from utils.config import contracts, get_deployer_account
from utils.voting import bake_vote_items
from utils.dual_governance import process_pending_proposals
from utils.evm_script import encode_call_script
from utils.import_current_votes import get_vote_script_files, get_upgrade_script_files
from utils.mainnet_fork import pass_and_exec_dao_vote

def main():
    processed_proposal_ids = process_pending_proposals()
    execute_votings_and_process_created_proposals(processed_proposal_ids)

def execute_votings_and_process_created_proposals(processed_proposal_ids: list[int]):
    votings_in_flight = retrieve_votings_in_flight()

    votings_to_execute = list(votings_in_flight)
    post_vote_on_fork = None
    proposal_ids_from_env = get_active_proposals_from_env()
    processed_env_proposal = set(processed_proposal_ids) & set(proposal_ids_from_env)

    if proposal_ids_from_env:
        # DG_PROPOSAL_IDS is set: the proposal already exists on-chain and the vote that
        # submitted it was already enacted (e.g. the fork is taken from mainnet while the
        # proposal is still in its DG waiting period). Running the vote script again would
        # start and enact a duplicate vote and revert on the already-applied state. The
        # pending proposal itself is executed by process_pending_proposals() in main().
        # Mirrors the test fixtures, which skip vote execution when proposal ids come from env.
        print("DG_PROPOSAL_IDS is set, skipping vote script execution.")
        vote_script = retrieve_vote_script() if processed_env_proposal else None
    else:
        vote_script = retrieve_vote_script()

    if vote_script:
        start_vote, get_vote_items, post_vote_on_fork = vote_script

        is_already_in_flight = bool(proposal_ids_from_env) or any(
            is_vote_script_equal_to_voting_in_flight(vote_id, get_vote_items)
            for vote_id in votings_in_flight
        )

        if not is_already_in_flight:
            print("Starting a new voting from script...")
            new_vote_id, _ = start_vote(tx_params={"from": get_deployer_account()}, silent=True)
            votings_to_execute.append(new_vote_id)

    if not votings_to_execute:
        print("No votings to execute.")
        if post_vote_on_fork and processed_env_proposal:
            post_vote_on_fork()
        return

    print(f"Passing and enacting votings: {votings_to_execute}")
    for vote_id in votings_to_execute:
        pass_and_exec_dao_vote(vote_id=vote_id)

    if post_vote_on_fork:
        post_vote_on_fork()

def is_vote_script_equal_to_voting_in_flight(
    voting_id: int, get_vote_items: Callable[[], Tuple[List, List]]
):
    onchain_vote_script = contracts.voting.getVote(voting_id)["script"]

    vote_desc_items, call_script_items = get_vote_items()
    local_vote_items = bake_vote_items(list(vote_desc_items), list(call_script_items))
    local_evm_script = encode_call_script(local_vote_items.values())

    return local_evm_script == onchain_vote_script

def retrieve_votings_in_flight() -> List[int]:
    votings_in_flight = []
    last_vote_id = contracts.voting.votesLength() - 1

    while last_vote_id >= 0:
        vote_phase = contracts.voting.getVotePhase(last_vote_id)

        if vote_phase == 2:
            break

        vote = contracts.voting.getVote(last_vote_id)

        min_quorum = vote["votingPower"] * vote["minAcceptQuorum"] // contracts.voting.PCT_BASE()
        is_vote_passing = vote["yea"] > min_quorum and vote["yea"] > vote["nay"]

        if vote_phase == 0 or (vote_phase == 1 and is_vote_passing):
            votings_in_flight.insert(0, last_vote_id)
        last_vote_id -= 1

    if votings_in_flight:
        print(f"Found votings in flight: {votings_in_flight}")
    return votings_in_flight

def retrieve_vote_script() -> Tuple[Callable, Callable, Callable | None] | None:
    vote_files = get_vote_script_files()
    vote_files.extend(get_upgrade_script_files())

    if not vote_files:
        return None

    if len(vote_files) > 1:
        raise RuntimeError("More than one vote script found.")

    script_path = sorted(vote_files)[0] # the expectation is that the only voting exists at the same time
    print(f"Found vote script: {script_path}")

    script_name = os.path.splitext(os.path.basename(script_path))[0]
    module_name = f"scripts.{script_name}"

    try:
        exec(f"from {module_name} import start_vote, get_vote_items")
        try:
            exec(f"from {module_name} import post_vote_on_fork")
        except ImportError:
            pass
        return locals()['start_vote'], locals()['get_vote_items'], locals().get('post_vote_on_fork')
    except ImportError:
        raise AttributeError(
            f"'start_vote' and/or 'get_vote_items' not found in {script_path}."
        )
    except Exception as e:
        raise RuntimeError(f"An unexpected error occurred while importing from {script_path}: {e}")
