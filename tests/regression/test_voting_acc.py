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
    with reverts("VOTING_NO_VOTING_POWER"):
        contracts.voting.vote(vote_id, True, False, {"from": stranger})
    with reverts("VOTING_NO_VOTING_POWER"):
        contracts.voting.vote(vote_id, False, False, {"from": stranger})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime() + 1)
    chain.mine()

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, True, False, {"from": stranger})
    with reverts("VOTING_NO_VOTING_POWER"):
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
# [main] delegate vote for YES holders 1,2 (reject no delegation)
# [main] holders 0,1 delegate to delegate
# [main] delegate vote for YES holder 3 (reject not a delegation for holder 3)
# [main] delegate vote for YES holders 1,2,3 (vote for 1 and 2 not 3)
# [main] delegate revote for NO holders 1,2
# [main] holder 3 delegate to delegate
# [main] delegate vote for YES holders 3
# [main] holder 3 vote for NO
# [main] holder 2 delegate to holder 3
# [main] holder 1 reset delegate
# [main] delegate revote for YES holders 1 (reject not a delegate)
# [main] delegate revote for YES holders 2 (reject not a delegate)
# [main] delegate revote for YES holders 3 (reject cant overpower holder)
# [main] holders 1,2,3 can revote main phase YES
# [objc] holders 1,2,3 can revote NO
# [objc] delegate revote NO (reject)
"""
def test_simple_delegation(call_target, delegate, test_vote):
    vote_id = test_vote[0]

    holder1 = LDO_VOTE_EXECUTORS_FOR_TESTS[0]
    holder2 = LDO_VOTE_EXECUTORS_FOR_TESTS[1]
    holder3 = LDO_VOTE_EXECUTORS_FOR_TESTS[2]

    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase
    # [main] delegate vote for YES holders 1 (reject no delegation)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        # if you don't have this func in object update abi
        contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})

    # [main] holders 0,1 delegate to delegate
    for holder in [holder1, holder2]:
        contracts.voting.setDelegate(delegate, {"from": accounts.at(holder, force=True)})

    # [main] delegate vote for YES holder 3 (reject not a delegation for holder 3)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})

    # [main] delegate vote for YES holders 1,2 (vote for 1 and 2)
    contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})
    contracts.voting.attemptVoteFor(vote_id, True, holder2, {"from": delegate})

    # [main] delegate revote for NO holders 1,2
    contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})
    contracts.voting.attemptVoteFor(vote_id, True, holder2, {"from": delegate})

    # [main] holder 3 delegate to delegate
    contracts.voting.setDelegate(delegate, {"from": accounts.at(holder3, force=True)})

    holders = contracts.voting.getDelegatedVoters(delegate, 0 , 5)
    assert holders[0] == [holder1, holder2, holder3]

    # [main] delegate vote for YES holders 3
    contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})

    # [main] holder 3 vote for NO
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder3, force=True)})

    # [main] holder 2 delegate to holder 3
    contracts.voting.setDelegate(holder3, {"from": accounts.at(holder2, force=True)})

    # [main] holder 1 reset delegate
    contracts.voting.resetDelegate({"from": accounts.at(holder1, force=True)})

    # [main] delegate revote for YES holders 1-3 (reject)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})

    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder2, {"from": delegate})

    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})

    holders = contracts.voting.getDelegatedVoters(delegate, 0, 5)
    assert holders[0] == [holder3]

    # [main] holders 1,2,3 can revote main phase YES
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, True, False, {"from": accounts.at(holder, force=True)})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
    chain.mine()

    assert contracts.voting.getVotePhase(vote_id) == 1  # Objection phase

    # [objc] holders 1,2,3 can revote NO
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder, force=True)})

    # [objc] delegate revote NO (reject)
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.attemptVoteFor(vote_id, True, holder2, {"from": delegate})

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})


"""
# [main] delegate vote for YES holders 1,2 (reject no delegation)
# [main] holders 0,1 delegate to delegate
# [main] delegate vote for YES holder 3 (reject not a delegation for holder 3)
# [main] delegate vote for YES holders 1,2,3 (vote for 1 and 2 not 3)
# [main] delegate revote for NO holders 1,2
# [main] holder 3 delegate to delegate
# [main] delegate vote for YES holders 3
# [main] holder 3 vote for NO
# [main] holder 2 delegate to holder 3
# [main] holder 1 reset delegate
# [main] delegate revote for YES holders 1-3 (reject)
# [main] delegate revote for YES holders 1 (reject not a delegate)
# [main] delegate revote for YES holders 2 (reject not a delegate)
# [main] delegate revote for YES holders 3 (reject cant overpower holder)
# [main] holders 1,2,3 can revote main phase YES
# [objc] holders 1,2,3 can revote NO
# [objc] delegate revote NO (reject)
"""
def test_simple_delegation_multi(call_target, delegate, test_vote):
    vote_id = test_vote[0]

    holder1 = LDO_VOTE_EXECUTORS_FOR_TESTS[0]
    holder2 = LDO_VOTE_EXECUTORS_FOR_TESTS[1]
    holder3 = LDO_VOTE_EXECUTORS_FOR_TESTS[2]

    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase
    # [main] delegate vote for YES holders 1,2 (reject no delegation)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        # if you don't have this func in object update abi
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2], {"from": delegate})

    # [main] holders 0,1 delegate to delegate
    for holder in [holder1, holder2]:
        contracts.voting.setDelegate(delegate, {"from": accounts.at(holder, force=True)})

    # [main] delegate vote for YES holder 3 (reject not a delegation for holder 3)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": delegate})

    # [main] delegate vote for YES holders 1,2,3 (vote for 1 and 2 not 3)
    contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2, holder3], {"from": delegate})

    # [main] delegate revote for NO holders 1,2
    contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2], {"from": delegate})

    # [main] holder 3 delegate to delegate
    contracts.voting.setDelegate(delegate, {"from": accounts.at(holder3, force=True)})

    holders = contracts.voting.getDelegatedVoters(delegate, 0 , 5)
    assert holders[0] == [holder1, holder2, holder3]

    # [main] delegate vote for YES holders 3
    contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": delegate})

    # [main] holder 3 vote for NO
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder3, force=True)})

    # [main] holder 2 delegate to holder 3
    contracts.voting.setDelegate(holder3, {"from": accounts.at(holder2, force=True)})

    # [main] holder 1 reset delegate
    contracts.voting.resetDelegate({"from": accounts.at(holder1, force=True)})

    # [main] delegate revote for YES holders 1-3 (reject)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2, holder3], {"from": delegate})

    holders = contracts.voting.getDelegatedVoters(delegate, 0, 5)
    assert holders[0] == [holder3]

    # [main] delegate revote for YES holders 1 (reject not a delegate)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1], {"from": delegate})

    # [main] delegate revote for YES holders 2 (reject not a delegate)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
       contracts.voting.attemptVoteForMultiple(vote_id, True, [holder2], {"from": delegate})

    # [main] delegate revote for YES holders 3 (reject cant overpower holder)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": delegate})

    # [main] holders 1,2,3 can revote main phase YES
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, True, False, {"from": accounts.at(holder, force=True)})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
    chain.mine()

    assert contracts.voting.getVotePhase(vote_id) == 1  # Objection phase

    # [objc] holders 1,2,3 can revote NO
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder, force=True)})

    # [objc] delegate revote NO (reject)
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2, holder3], {"from": delegate})
