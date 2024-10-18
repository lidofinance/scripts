from typing import Dict

import pytest

from brownie import accounts, chain, MockCallTarget, multicall
from web3 import Web3

from utils.test.snapshot_helpers import ValueChanged, dict_zip, dict_diff, assert_no_diffs, assert_expected_diffs

from utils.voting import create_vote, bake_vote_items
from utils.config import (
    LDO_VOTE_EXECUTORS_FOR_TESTS,
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    contracts,
)
from utils.import_current_votes import start_and_execute_votes


@pytest.fixture(scope="module")
def vote_time():
    return contracts.voting.voteTime()


@pytest.fixture(scope="module", autouse=True)
def call_target():
    return MockCallTarget.deploy({"from": accounts[0]})


def snapshot(voting, vote_id):
    block = chain.height
    length = voting.votesLength()
    vote = voting.getVote(vote_id)
    result = {}

    with multicall(block_identifier=block):
        result |= {
            "address": voting.address,
            "voteTime": voting.voteTime(),
            "CREATE_VOTES_ROLE": voting.CREATE_VOTES_ROLE(),
            "MODIFY_SUPPORT_ROLE": voting.MODIFY_SUPPORT_ROLE(),
            "MODIFY_QUORUM_ROLE": voting.MODIFY_QUORUM_ROLE(),
            "UNSAFELY_MODIFY_VOTE_TIME_ROLE": voting.UNSAFELY_MODIFY_VOTE_TIME_ROLE(),
            "PCT_BASE": voting.PCT_BASE(),
            "minAcceptQuorumPct": voting.minAcceptQuorumPct(),
            "supportRequiredPct": voting.supportRequiredPct(),
            "votesLength": length,
            "objectionPhaseTime": voting.objectionPhaseTime(),
            "token": voting.token(),
            "vote_open": vote[0],
            "vote_executed": vote[1],
            "vote_supportRequired": vote[4],
            "vote_minAcceptQuorum": vote[5],
            "vote_yea": vote[6],
            "vote_nay": vote[7],
            "vote_votingPower": vote[8],
            "vote_script": vote[9],
            "vote_canExecute": voting.canExecute(vote_id),
            "vote_voter1_state": voting.getVoterState(vote_id, LDO_VOTE_EXECUTORS_FOR_TESTS[0]),
            "vote_voter2_state": voting.getVoterState(vote_id, LDO_VOTE_EXECUTORS_FOR_TESTS[1]),
            "vote_voter3_state": voting.getVoterState(vote_id, LDO_VOTE_EXECUTORS_FOR_TESTS[2]),
        }

    return result


def steps(voting, call_target, vote_time) -> Dict[str, Dict[str, ValueChanged]]:
    result = {}

    params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
    vote_items = [(call_target.address, call_target.perform_call.encode_input())]
    vote_id = create_vote(bake_vote_items(["Test voting"], vote_items), params)[0]
    result["create"] = snapshot(voting, vote_id)

    for indx, voter in enumerate(LDO_VOTE_EXECUTORS_FOR_TESTS):
        account = accounts.at(voter, force=True)
        voting.vote(vote_id, True, False, {"from": account})
        result[f"vote_#{indx}"] = snapshot(voting, vote_id)

    chain.sleep(vote_time + 100)
    chain.mine()
    result["wait"] = snapshot(voting, vote_id)

    assert not call_target.called()

    voting.executeVote(vote_id, {"from": LDO_HOLDER_ADDRESS_FOR_TESTS})

    assert call_target.called()

    result["enact"] = snapshot(voting, vote_id)
    return result


def test_create_wait_enact(helpers, vote_time, call_target, vote_ids_from_env):
    """
    Run a smoke test before upgrade, then after upgrade, and compare snapshots at each step
    """
    votesLength = contracts.voting.votesLength()
    before: Dict[str, Dict[str, any]] = steps(contracts.voting, call_target, vote_time)
    chain.revert()

    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting)
    else:
        start_and_execute_votes(contracts.voting, helpers)
    after: Dict[str, Dict[str, any]] = steps(contracts.voting, call_target, vote_time)

    step_diffs: Dict[str, Dict[str, ValueChanged]] = {}

    for step, pair_of_snapshots in dict_zip(before, after).items():
        (before, after) = pair_of_snapshots
        step_diffs[step] = dict_diff(before, after)

    for step_name, diff in step_diffs.items():
        if not vote_ids_from_env:
            assert_expected_diffs(
                step_name, diff, {"votesLength": ValueChanged(from_val=votesLength + 1, to_val=votesLength + 2)}
            )
        assert_no_diffs(step_name, diff)


def create_dummy_vote(ldo_holder: str) -> int:
    vote_items = bake_vote_items(vote_desc_items=[], call_script_items=[])
    return create_vote(vote_items, {"from": ldo_holder}, cast_vote=False, executes_if_decided=False)[0]
