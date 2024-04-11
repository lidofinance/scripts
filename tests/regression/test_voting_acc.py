"""
Tests for lido staking limits
"""
from typing import Tuple, Optional

import pytest

from brownie import MockCallTarget, accounts, chain, reverts, interface, ZERO_ADDRESS
from brownie.network.transaction import TransactionReceipt
from utils.voting import create_vote, bake_vote_items
from utils.config import LDO_VOTE_EXECUTORS_FOR_TESTS
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.config import contracts


@pytest.fixture(scope="module")
def call_target():
    return MockCallTarget.deploy({"from": accounts[0]})


@pytest.fixture(scope="module")
def test_trp_escrow(trp_recipient, ldo_holder):
    contracts.ldo_token.approve(
        contracts.trp_escrow_factory.address, 1_000_000_000_000_000_000, {"from": accounts.at(ldo_holder, force=True)}
    )

    tx = contracts.trp_escrow_factory.deploy_vesting_contract(
        1_000_000_000_000_000_000,
        trp_recipient.address,
        360,
        chain.time(),  # bc of tests can be in future
        24,
        1,
        {"from": accounts.at(ldo_holder, force=True)},
    )

    print(f"{tx.events['VestingEscrowCreated'][0][0]}")
    escrow_address = tx.events["VestingEscrowCreated"][0][0]["escrow"]
    chain.mine()

    return escrow_address


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
# [main] holders 0,1 delegate to 'delegate'
# [main] delegate vote for YES holder 3 (reject not a delegation for holder 3)
# [main] delegate vote for YES holders 1,2,3 (vote for 1 and 2 not 3)
# [main] delegate re-vote for NO holders 1,2
# [main] holder 3 delegate to 'delegate'
# [main] delegate vote for YES holders 3
# [main] holder 3 vote for NO
# [main] holder 2 delegate to holder 3
# [main] holder 1 reset delegate
# [main] delegate re-vote for YES holders 1 (reject not a delegate)
# [main] delegate re-vote for YES holders 2 (reject not a delegate)
# [main] delegate re-vote for YES holders 3 (reject cant overpower holder)
# [main] holders 1,2,3 can re-vote main phase YES
# [objc] holders 1,2,3 can re-vote NO
# [objc] delegate re-vote NO (reject)
"""


def test_simple_delegation(delegate, test_vote):
    vote_id = test_vote[0]

    holder1 = LDO_VOTE_EXECUTORS_FOR_TESTS[0]
    holder2 = LDO_VOTE_EXECUTORS_FOR_TESTS[1]
    holder3 = LDO_VOTE_EXECUTORS_FOR_TESTS[2]

    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase
    # [main] delegate vote for YES holders 1 (reject no delegation)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        # if you don't have this func in object, update abi
        contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})

    # [main] holders 0,1 delegate to 'delegate'
    for holder in [holder1, holder2]:
        contracts.voting.setDelegate(delegate, {"from": accounts.at(holder, force=True)})

    # [main] delegate vote for YEA holder 3 (reject not a delegation for holder 3)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})

    # [main] delegate vote for YEA holders 1,2 (vote for 1 and 2)
    contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})
    contracts.voting.attemptVoteFor(vote_id, True, holder2, {"from": delegate})

    # [main] delegate re-vote for NAY holders 1,2
    contracts.voting.attemptVoteFor(vote_id, False, holder1, {"from": delegate})
    contracts.voting.attemptVoteFor(vote_id, False, holder2, {"from": delegate})

    # [main] holder 3 delegate to 'delegate'
    contracts.voting.setDelegate(delegate, {"from": accounts.at(holder3, force=True)})

    holders = contracts.voting.getDelegatedVoters(delegate, 0, 5)
    assert holders[0] == [holder1, holder2, holder3]
    for holder in holders[0]:
        assert contracts.voting.getDelegate(holder) == delegate

    # [main] delegate vote for YEA holders 3
    contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})

    # [main] holder 3 vote for NAY
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder3, force=True)})

    # [main] holder 2 delegate to holder 3
    contracts.voting.setDelegate(holder3, {"from": accounts.at(holder2, force=True)})

    assert contracts.voting.getDelegate(holder2) == holder3

    # [main] holder 1 reset delegate
    contracts.voting.resetDelegate({"from": accounts.at(holder1, force=True)})

    assert contracts.voting.getDelegate(holder1) == ZERO_ADDRESS

    # [main] delegate re-vote for YES holders 1-3 (reject)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})

    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder2, {"from": delegate})

    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})

    holders = contracts.voting.getDelegatedVoters(delegate, 0, 5)
    assert holders[0] == [holder3]
    assert contracts.voting.getDelegate(holder3) == delegate

    # [main] holders 1,2,3 can re-vote main phase YEA
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, True, False, {"from": accounts.at(holder, force=True)})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
    chain.mine()

    assert contracts.voting.getVotePhase(vote_id) == 1  # Objection phase

    # [objc] holders 1,2,3 can re-vote NAY
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder, force=True)})

    # [objc] delegate re-vote NAY (reject)
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.attemptVoteFor(vote_id, True, holder2, {"from": delegate})

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})


"""
# [main] delegate vote for YEA holders 1,2 (reject no delegation)
# [main] holders 0,1 delegate to 'delegate'
# [main] delegate vote for YEA holder 3 (reject not a delegation for holder 3)
# [main] delegate vote for YEA holders 1,2,3 (vote for 1 and 2 not 3)
# [main] delegate re-vote for NAY holders 1,2
# [main] holder 3 delegate to 'delegate'
# [main] delegate vote for YEA holders 3
# [main] holder 3 vote for NAY
# [main] holder 2 delegate to holder 3
# [main] holder 1 reset delegate
# [main] delegate re-vote for YEA holders 1-3 (reject)
# [main] delegate re-vote for YEA holders 1 (reject not a delegate)
# [main] delegate re-vote for YEA holders 2 (reject not a delegate)
# [main] delegate re-vote for YEA holders 3 (reject cant overpower holder)
# [main] holders 1,2,3 can re-vote main phase YEA
# [objc] holders 1,2,3 can re-vote NAY
# [objc] delegate re-vote NAY (reject)
"""


def test_simple_delegation_multiple(delegate, test_vote):
    vote_id = test_vote[0]

    holder1 = LDO_VOTE_EXECUTORS_FOR_TESTS[0]
    holder2 = LDO_VOTE_EXECUTORS_FOR_TESTS[1]
    holder3 = LDO_VOTE_EXECUTORS_FOR_TESTS[2]

    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase
    # [main] delegate vote for YEA holders 1,2 (reject no delegation)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        # if you don't have this func in object, update abi
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2], {"from": delegate})

    # [main] holders 0,1 delegate to 'delegate'
    for holder in [holder1, holder2]:
        contracts.voting.setDelegate(delegate, {"from": accounts.at(holder, force=True)})

    # [main] delegate vote for YEA holder 3 (reject not a delegation for holder 3)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": delegate})

    # [main] delegate vote for YEA holders 1,2,3 (vote for 1 and 2 not 3)
    contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2, holder3], {"from": delegate})

    # [main] delegate re-vote for NAY holders 1,2
    contracts.voting.attemptVoteForMultiple(vote_id, False, [holder1, holder2], {"from": delegate})

    # [main] holder 3 delegate to 'delegate'
    contracts.voting.setDelegate(delegate, {"from": accounts.at(holder3, force=True)})

    holders = contracts.voting.getDelegatedVoters(delegate, 0, 5)
    assert holders[0] == [holder1, holder2, holder3]
    for holder in holders[0]:
        assert contracts.voting.getDelegate(holder) == delegate

    # [main] delegate vote for YEA holders 3
    contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": delegate})

    # [main] holder 3 vote for NAY
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder3, force=True)})

    # [main] holder 2 delegate to holder 3
    contracts.voting.setDelegate(holder3, {"from": accounts.at(holder2, force=True)})

    # [main] holder 1 reset delegate
    contracts.voting.resetDelegate({"from": accounts.at(holder1, force=True)})

    # [main] delegate re-vote for YEA holders 1-3 (reject)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2, holder3], {"from": delegate})

    holders = contracts.voting.getDelegatedVoters(delegate, 0, 5)
    assert holders[0] == [holder3]
    assert contracts.voting.getDelegate(holder3) == delegate

    # [main] delegate re-vote for YEA holders 1 (reject not a delegate)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1], {"from": delegate})

    # [main] delegate re-vote for YEA holders 2 (reject not a delegate)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder2], {"from": delegate})

    # [main] delegate re-vote for YEA holders 3 (reject cant overpower holder)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder3], {"from": delegate})

    # [main] holders 1,2,3 can re-vote main phase YEA
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, True, False, {"from": accounts.at(holder, force=True)})

    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
    chain.mine()

    assert contracts.voting.getVotePhase(vote_id) == 1  # Objection phase

    # [objc] holders 1,2,3 can re-vote NAY
    for holder in [holder1, holder2, holder3]:
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(holder, force=True)})

    # [objc] delegate re-vote NAY (reject)
    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.attemptVoteForMultiple(vote_id, True, [holder1, holder2, holder3], {"from": delegate})


def test_trp_delegation(test_trp_escrow, test_vote, delegate, trp_recipient):
    vote_id = test_vote[0]
    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

    trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
    trp_voting_adapter = interface.VotingAdapter(trp_voting_adapter_address)
    encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(delegate.address)

    trp_escrow_contract = interface.Escrow(test_trp_escrow)

    trp_escrow_contract.delegate(encoded_delegate_address, {"from": trp_recipient})

    delegated_voters = contracts.voting.getDelegatedVoters(delegate.address, 0, 5, {"from": delegate})
    assert delegated_voters[0] == [test_trp_escrow]
    assert contracts.voting.getDelegate(test_trp_escrow) == delegate

    vote_before = contracts.voting.getVote(vote_id, {"from": delegate})
    assert vote_before["yea"] == 0

    contracts.voting.attemptVoteFor(vote_id, True, test_trp_escrow, {"from": delegate})
    vote_after = contracts.voting.getVote(vote_id, {"from": delegate})
    assert vote_after["yea"] == 1_000_000_000_000_000_000

    encoded_zero_address = trp_voting_adapter.encode_delegate_calldata(ZERO_ADDRESS)

    trp_escrow_contract.delegate(encoded_zero_address, {"from": trp_recipient})
    assert contracts.voting.getDelegate(trp_recipient) == ZERO_ADDRESS


def test_trp_delegation_multiple(test_trp_escrow, test_vote, delegate, trp_recipient):
    vote_id = test_vote[0]
    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

    trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
    trp_voting_adapter = interface.VotingAdapter(trp_voting_adapter_address)
    encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(delegate.address)

    interface.Escrow(test_trp_escrow).delegate(encoded_delegate_address, {"from": trp_recipient})

    contracts.voting.getDelegatedVoters(delegate.address, 0, 5, {"from": delegate})

    vote_before = contracts.voting.getVote(vote_id, {"from": delegate})
    assert vote_before["yea"] == 0

    contracts.voting.attemptVoteForMultiple(vote_id, True, [test_trp_escrow], {"from": delegate})
    vote_after = contracts.voting.getVote(vote_id, {"from": delegate})
    assert vote_after["yea"] == 1_000_000_000_000_000_000
