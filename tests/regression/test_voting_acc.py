"""
Tests for lido staking limits
"""
from typing import Tuple, Optional

import pytest

from brownie import MockCallTarget, accounts, chain, reverts
from brownie.network.transaction import TransactionReceipt
from utils.voting import create_vote, bake_vote_items
from utils.config import LDO_VOTE_EXECUTORS_FOR_TESTS
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.config import contracts


@pytest.fixture(scope="module")
def call_target():
    return MockCallTarget.deploy({"from": accounts[0]})


@pytest.fixture(scope="function")
def test_vote(ldo_holder, call_target) -> Tuple[int, Optional[TransactionReceipt]]:
    vote_items = [(call_target.address, call_target.perform_call.encode_input())]
    return create_vote(bake_vote_items(["Test voting"], vote_items), {"from": ldo_holder})


def test_stranger_cant_do_anything(test_vote, stranger):
    with reverts("APP_AUTH_FAILED"):
        contracts.voting.newVote(EMPTY_CALLSCRIPT, "Test", {"from": stranger})

    vote_id = test_vote[0]
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, True, False, {"from": stranger})
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, False, False, {"from": stranger})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime() + 1)
    chain.mine()

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, True, False, {"from": stranger})
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, False, False, {"from": stranger})

    chain.sleep(contracts.voting.objectionPhaseTime())
    chain.mine()

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, True, False, {"from": stranger})
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, False, False, {"from": stranger})


def test_non_existant_vote(ldo_holder, stranger):
    vote_id = contracts.voting.votesLength()  # wrong vote_id

    with reverts("VOTING_NO_VOTE"):
        contracts.voting.vote(vote_id, True, False, {"from": ldo_holder})

    with reverts("VOTING_NO_VOTE"):
        contracts.voting.executeVote(vote_id, {"from": stranger})


def test_phases(call_target, stranger, test_vote):
    vote_id = test_vote[0]

    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

    for voter in LDO_VOTE_EXECUTORS_FOR_TESTS:
        contracts.voting.vote(vote_id, True, False, {"from": accounts.at(voter, force=True)})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
    chain.mine()

    assert contracts.voting.getVotePhase(vote_id) == 1  # Objection phase

    # change the previous vote to object
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[2], force=True)})

    with reverts("VOTING_CAN_NOT_EXECUTE"):
        contracts.voting.executeVote(vote_id, {"from": stranger})

    chain.sleep(contracts.voting.objectionPhaseTime())
    chain.mine()

    assert contracts.voting.getVotePhase(vote_id) == 2  # Closed phase

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[2], force=True)})

    assert not call_target.called()
    contracts.voting.executeVote(vote_id, {"from": stranger})
    assert call_target.called()


def test_can_object(stranger, test_vote):
    vote_id = test_vote[0]

    for voter in LDO_VOTE_EXECUTORS_FOR_TESTS[1:]:
        contracts.voting.vote(vote_id, True, False, {"from": accounts.at(voter, force=True)})

    # change the vote to ney
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[2], force=True)})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
    chain.mine()

    # change the vote to yay again but late
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, True, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[2], force=True)})

    # fresh objection
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[0], force=True)})

    chain.sleep(contracts.voting.objectionPhaseTime())
    chain.mine()

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[2], force=True)})

    # rejected vote cannot be executed
    with reverts("VOTING_CAN_NOT_EXECUTE"):
        contracts.voting.executeVote(vote_id, {"from": stranger})

"""
# stranger vote for YES holders 1,2 (reject no delegation)
# holders 0,1 delegate to stranger
# stranger vote for YES holder 3 (reject not a delegation for holder 3)
# stranger vote for YES holders 1,2,3 (reject not a delegation for holder 3)
#  stranger revote for NO holders 1,2
# holder 3 delegate to stranger
# stranger vote for YES holders 3
#  holder 3 vote for NO
#  holder 2 delegate to holder 3
#  holder 1 reset delegate
# stranger revote for YES holders 1-3 (reject)
# stranger revote for YES holders 1 (reject not a delegate)
# stranger revote for YES holders 2 (reject not a delegate)
# stranger revote for YES holders 3 (reject cant overpower holder)
# holders 1,2,3 can revote main phase YES
# holders 1,2,3 can revote objection phase NO
"""

def test_attempt_vote_for_multi(call_target, stranger, test_vote):
    vote_id = test_vote[0]

    holder1 = LDO_VOTE_EXECUTORS_FOR_TESTS[0]
    holder2 = LDO_VOTE_EXECUTORS_FOR_TESTS[1]
    holder3 = LDO_VOTE_EXECUTORS_FOR_TESTS[3]

    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase
    # stranger vote for YES holders 1,2 (reject no delegation)
    with reverts("REJECT"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2], {"from": stranger})

    # holders 0,1 delegate to stranger
    for holder in [holder1, holder2]:
        contracts.voting.setDelegate(stranger, {"from": accounts.at(holder, force=True)})

    # stranger vote for YES holder 3 (reject not a delegation for holder 3)
    with reverts("REJECT"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": stranger})

    # stranger vote for YES holders 1,2,3 (reject not a delegation for holder 3)
    with reverts("REJECT"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2, holder3], {"from": stranger})

    #  stranger revote for NO holders 1,2
    contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2], {"from": stranger})

    # holder 3 delegate to stranger
    contracts.voting.setDelegate(stranger, {"from": accounts.at(holder3, force=True)})

    holders = contracts.voting.getDelegatedVoters(stranger, 0 , 5)
    assert holders == [holder1, holder2, holder3]

    # stranger vote for YES holders 3
    contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": stranger})

    #  holder 3 vote for NO
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder3, force=True)})

    #  holder 2 delegate to holder 3
    contracts.voting.setDelegate(holder3, {"from": accounts.at(holder2, force=True)})

    #  holder 1 reset delegate
    contracts.voting.resetDelegate({"from": accounts.at(holder1, force=True)})

    # stranger revote for YES holders 1-3 (reject)
    with reverts("REJECT"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2, holder3], {"from": stranger})

    holders = contracts.voting.getDelegatedVoters(stranger, 0 , 5)
    assert holders == [holder3]

    # stranger revote for YES holders 1 (reject not a delegate)
    with reverts("REJECT"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1], {"from": stranger})

    # stranger revote for YES holders 2 (reject not a delegate)
    with reverts("REJECT"):
       contracts.voting.attemptVoteForMultiple(vote_id, True, [holder2], {"from": stranger})

    # stranger revote for YES holders 3 (reject cant overpower holder)
    with reverts("REJECT"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": stranger})

    # holders 1,2,3 can revote main phase YES
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, True, False, {"from": accounts.at(holder, force=True)})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
    chain.mine()

    assert contracts.voting.getVotePhase(vote_id) == 1  # Objection phase

    # holders 1,2,3 can revote objection phase NO
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder, force=True)})
