"""
Tests for lido staking limits
"""
from typing import Tuple, Optional

import pytest

from brownie import MockCallTarget, accounts, chain, reverts
from brownie.network.transaction import TransactionReceipt

from utils.config import ldo_vote_executors_for_tests
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.import_current_votes import is_there_any_vote_scripts, start_and_execute_votes
from utils.voting import create_vote, bake_vote_items


@pytest.fixture(scope="module", autouse=is_there_any_vote_scripts())
def autoexecute_vote(vote_id_from_env, helpers, accounts, dao_voting):
    if vote_id_from_env:
        helpers.execute_vote(vote_id=vote_id_from_env, accounts=accounts, dao_voting=dao_voting, topup="0.5 ether")

    start_and_execute_votes(dao_voting, helpers)


@pytest.fixture(scope="module")
def call_target():
    return MockCallTarget.deploy({"from": accounts[0]})


@pytest.fixture(scope="module")
def stranger():
    return accounts[0]


@pytest.fixture(scope="module")
def test_vote(ldo_holder, call_target) -> Tuple[int, Optional[TransactionReceipt]]:
    vote_items = [(call_target.address, call_target.perform_call.encode_input())]
    return create_vote(bake_vote_items(["Test voting"], vote_items), {"from": ldo_holder})


def test_stranger_cant_do_anything(dao_voting, test_vote, stranger):
    with reverts("APP_AUTH_FAILED"):
        dao_voting.newVote(EMPTY_CALLSCRIPT, "Test", {"from": stranger})

    vote_id = test_vote[0]
    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, True, False, {"from": stranger})
    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, False, False, {"from": stranger})

    chain.sleep(dao_voting.voteTime() - dao_voting.objectionPhaseTime() + 1)
    chain.mine()

    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, True, False, {"from": stranger})
    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, False, False, {"from": stranger})

    chain.sleep(dao_voting.objectionPhaseTime())
    chain.mine()

    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, True, False, {"from": stranger})
    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, False, False, {"from": stranger})


def test_non_existant_vote(dao_voting, ldo_holder, stranger):
    vote_id = dao_voting.votesLength()  # wrong vote_id

    with reverts("VOTING_NO_VOTE"):
        dao_voting.vote(vote_id, True, False, {"from": ldo_holder})

    with reverts("VOTING_NO_VOTE"):
        dao_voting.executeVote(vote_id, {"from": stranger})


def test_phases(dao_voting, call_target, stranger, test_vote):
    vote_id = test_vote[0]

    assert dao_voting.getVotePhase(vote_id) == 0  # Main phase

    for voter in ldo_vote_executors_for_tests:
        dao_voting.vote(vote_id, True, False, {"from": accounts.at(voter, force=True)})

    chain.sleep(dao_voting.voteTime() - dao_voting.objectionPhaseTime())
    chain.mine()

    assert dao_voting.getVotePhase(vote_id) == 1  # Objection phase

    # change the previous vote to object
    dao_voting.vote(vote_id, False, False, {"from": accounts.at(ldo_vote_executors_for_tests[2], force=True)})

    with reverts("VOTING_CAN_NOT_EXECUTE"):
        dao_voting.executeVote(vote_id, {"from": stranger})

    chain.sleep(dao_voting.objectionPhaseTime())
    chain.mine()

    assert dao_voting.getVotePhase(vote_id) == 2  # Closed phase

    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, False, False, {"from": accounts.at(ldo_vote_executors_for_tests[2], force=True)})

    assert not call_target.called()
    dao_voting.executeVote(vote_id, {"from": stranger})
    assert call_target.called()


def test_can_object(dao_voting, call_target, stranger, test_vote):
    vote_id = test_vote[0]

    for voter in ldo_vote_executors_for_tests[1:]:
        dao_voting.vote(vote_id, True, False, {"from": accounts.at(voter, force=True)})

    # change the vote to ney
    dao_voting.vote(vote_id, False, False, {"from": accounts.at(ldo_vote_executors_for_tests[2], force=True)})

    chain.sleep(dao_voting.voteTime() - dao_voting.objectionPhaseTime())
    chain.mine()

    # change the vote to yay again but late
    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, True, False, {"from": accounts.at(ldo_vote_executors_for_tests[2], force=True)})

    # fresh objection
    dao_voting.vote(vote_id, False, False, {"from": accounts.at(ldo_vote_executors_for_tests[0], force=True)})

    chain.sleep(dao_voting.objectionPhaseTime())
    chain.mine()

    with reverts("VOTING_CAN_NOT_VOTE"):
        dao_voting.vote(vote_id, False, False, {"from": accounts.at(ldo_vote_executors_for_tests[2], force=True)})

    # rejected vote cannot be executed
    with reverts("VOTING_CAN_NOT_EXECUTE"):
        dao_voting.executeVote(vote_id, {"from": stranger})
