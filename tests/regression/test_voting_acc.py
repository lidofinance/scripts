"""
Tests for lido aragon voting app
"""
import os

from typing import Tuple, Optional
from enum import Enum
from web3 import Web3

import pytest

# import os

# from web3 import Web3
from brownie import MockCallTarget, accounts, chain, reverts, interface, ZERO_ADDRESS, web3
from brownie.network.transaction import TransactionReceipt
from brownie.network.event import _decode_logs
from utils.voting import create_vote, bake_vote_items
from utils.config import LDO_VOTE_EXECUTORS_FOR_TESTS, CHAIN_NETWORK_NAME
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.config import contracts, TRP_FACTORY_DEPLOY_BLOCK_NUMBER


class VoterState(Enum):
    Absent = 0
    Yea = 1
    Nay = 2
    DelegateYea = 3
    DelegateNay = 4


def filter_logs(logs, topic):
    return list(filter(lambda l: l["topics"][0] == topic, logs))


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


@pytest.fixture(scope="module")
def trp_voting_adapter():
    trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
    return interface.VotingAdapter(trp_voting_adapter_address)


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
    vote_tx = contracts.voting.vote(
        vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[2], force=True)}
    )
    assert vote_tx.events["CastVote"]["voteId"] == vote_id
    assert vote_tx.events["CastVote"]["voter"] == LDO_VOTE_EXECUTORS_FOR_TESTS[2]
    assert vote_tx.events["CastVote"]["supports"] == False

    with reverts("VOTING_CAN_NOT_EXECUTE"):
        contracts.voting.executeVote(vote_id, {"from": stranger})

    chain.sleep(contracts.voting.objectionPhaseTime())
    chain.mine()

    assert contracts.voting.getVotePhase(vote_id) == 2  # Closed phase

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[2], force=True)})

    assert not call_target.called()
    execute_tx = contracts.voting.executeVote(vote_id, {"from": stranger})
    assert execute_tx.events["ExecuteVote"]["voteId"] == vote_id
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
    vote_tx = contracts.voting.vote(
        vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[0], force=True)}
    )
    assert vote_tx.events["CastVote"]["voteId"] == vote_id
    assert vote_tx.events["CastVote"]["voter"] == LDO_VOTE_EXECUTORS_FOR_TESTS[0]
    assert vote_tx.events["CastVote"]["supports"] == False
    assert vote_tx.events["CastObjection"]["voteId"] == vote_id
    assert vote_tx.events["CastObjection"]["voter"] == LDO_VOTE_EXECUTORS_FOR_TESTS[0]

    chain.sleep(contracts.voting.objectionPhaseTime())
    chain.mine()

    with reverts("VOTING_CAN_NOT_VOTE"):
        contracts.voting.vote(vote_id, False, False, {"from": accounts.at(LDO_VOTE_EXECUTORS_FOR_TESTS[2], force=True)})

    # rejected vote cannot be executed
    with reverts("VOTING_CAN_NOT_EXECUTE"):
        contracts.voting.executeVote(vote_id, {"from": stranger})


def test_delegation_happy_path(delegate1, delegate2, test_vote, stranger):
    vote_id = test_vote[0]

    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

    voters = LDO_VOTE_EXECUTORS_FOR_TESTS

    # A delegate can not vote for a voter that has not assigned them
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, voters[0], {"from": delegate1})

    # A voter can assign a delegate
    assign_tx = contracts.voting.assignDelegate(delegate1, {"from": accounts.at(voters[0], force=True)})
    # Check event and state
    assert assign_tx.events["AssignDelegate"]["voter"] == voters[0]
    assert assign_tx.events["AssignDelegate"]["assignedDelegate"] == delegate1
    assert contracts.voting.getDelegate(voters[0]) == delegate1
    assert contracts.voting.getDelegatedVoters(delegate1, 0, 3)[0] == voters[0]

    contracts.voting.assignDelegate(delegate1, {"from": accounts.at(voters[1], force=True)})
    contracts.voting.assignDelegate(delegate1, {"from": accounts.at(voters[2], force=True)})

    # A voter can unassign the delegate
    unassign_tx = contracts.voting.unassignDelegate({"from": accounts.at(voters[0], force=True)})
    # Check event and state
    assert unassign_tx.events["UnassignDelegate"]["voter"] == voters[0]
    assert unassign_tx.events["UnassignDelegate"]["unassignedDelegate"] == delegate1
    assert contracts.voting.getDelegate(voters[0]) == ZERO_ADDRESS
    assert list(contracts.voting.getDelegatedVoters(delegate1, 0, 3)) == [voters[2], voters[1]]

    # A voter can change the delegate
    assign_tx = contracts.voting.assignDelegate(delegate2, {"from": accounts.at(voters[1], force=True)})
    # Check event and state
    assert assign_tx.events["AssignDelegate"]["voter"] == voters[1]
    assert assign_tx.events["AssignDelegate"]["assignedDelegate"] == delegate2
    assert contracts.voting.getDelegate(voters[1]) == delegate2
    assert list(contracts.voting.getDelegatedVoters(delegate2, 0, 3)) == [voters[1]]

    # A delegate can attempt to vote for multiple voters
    vote_for_tx = contracts.voting.attemptVoteForMultiple(vote_id, True, voters, {"from": delegate1})
    # Check events and state
    assert vote_for_tx.events.count("CastVote") == 1  # only one eligible voter left
    assert vote_for_tx.events["CastVote"]["voteId"] == vote_id
    assert vote_for_tx.events["CastVote"]["voter"] == voters[2]
    assert vote_for_tx.events["CastVote"]["supports"] == True
    assert vote_for_tx.events["AttemptCastVoteAsDelegate"]["voteId"] == vote_id
    assert vote_for_tx.events["AttemptCastVoteAsDelegate"]["delegate"] == delegate1
    assert list(vote_for_tx.events["AttemptCastVoteAsDelegate"]["voters"]) == voters
    assert contracts.voting.getVoterState(vote_id, voters[0]) == VoterState.Absent.value
    assert contracts.voting.getVoterState(vote_id, voters[1]) == VoterState.Absent.value
    assert contracts.voting.getVoterState(vote_id, voters[2]) == VoterState.DelegateYea.value
    assert contracts.voting.getVote(vote_id)["yea"] == contracts.ldo_token.balanceOf(voters[2])

    # A delegate can change their mind and vote for the opposite
    vote_for_tx = contracts.voting.attemptVoteFor(vote_id, False, voters[2], {"from": delegate1})
    # Check events and state
    assert contracts.voting.getVoterState(vote_id, voters[2]) == VoterState.DelegateNay.value
    assert contracts.voting.getVote(vote_id)["nay"] == contracts.ldo_token.balanceOf(voters[2])

    # A voter can overwrite the delegate vote
    contracts.voting.vote(vote_id, True, False, {"from": accounts.at(voters[2], force=True)})
    assert contracts.voting.getVoterState(vote_id, voters[2]) == VoterState.Yea.value
    assert contracts.voting.getVote(vote_id)["yea"] == contracts.ldo_token.balanceOf(voters[2])
    assert contracts.voting.getVote(vote_id)["nay"] == 0
    # A delegate can not overwrite the vote of the voter
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, voters[2], {"from": delegate1})

    # Prepare state for the next test
    chain.snapshot()
    contracts.voting.attemptVoteFor(vote_id, True, voters[1], {"from": delegate2})
    contracts.voting.assignDelegate(delegate1, {"from": accounts.at(voters[0], force=True)})
    contracts.voting.attemptVoteFor(vote_id, True, voters[0], {"from": delegate1})
    # Fast-forward to the objection phase
    chain.sleep(contracts.voting.voteTime() - contracts.voting.objectionPhaseTime())
    chain.mine()
    assert contracts.voting.getVotePhase(vote_id) == 1  # Objection phase

    # A delegate can not vote for a voter that overwrote their vote during the objection phase
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, False, voters[2], {"from": delegate1})
    # A voter can overwrite the delegate vote during the objection phase
    contracts.voting.vote(vote_id, False, False, {"from": accounts.at(voters[1], force=True)})
    assert contracts.voting.getVoterState(vote_id, voters[1]) == VoterState.Nay.value
    # A delegate can vote for a voter during the objection phase
    contracts.voting.attemptVoteFor(vote_id, False, voters[0], {"from": delegate1})

    # A vote can be safely executed
    chain.revert()
    # Add some more VP to be able to execute the vote
    contracts.voting.attemptVoteFor(vote_id, True, voters[1], {"from": delegate2})
    # Fast-forward to the closed phase
    chain.sleep(contracts.voting.voteTime())
    chain.mine()
    assert contracts.voting.getVotePhase(vote_id) == 2  # Closed phase
    # Execute the vote
    execute_tx = contracts.voting.executeVote(vote_id, {"from": stranger})
    assert execute_tx.events["ExecuteVote"]["voteId"] == vote_id


def test_delegation_trp(test_trp_escrow, test_vote, delegate1, trp_recipient, trp_voting_adapter):
    trp_escrow_contract = interface.Escrow(test_trp_escrow)
    vote_id = test_vote[0]
    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

    # A TRP participant can assign a delegate
    encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(delegate1.address)
    assign_tx = trp_escrow_contract.delegate(encoded_delegate_address, {"from": trp_recipient})
    # Check event and state
    assert assign_tx.events["AssignDelegate"]["voter"] == test_trp_escrow
    assert assign_tx.events["AssignDelegate"]["assignedDelegate"] == delegate1
    assert contracts.voting.getDelegate(test_trp_escrow) == delegate1
    assert contracts.voting.getDelegatedVoters(delegate1, 0, 3)[0] == test_trp_escrow

    # A TRP participant can unassign the delegate
    encoded_zero_address = trp_voting_adapter.encode_delegate_calldata(ZERO_ADDRESS)
    unassign_tx = trp_escrow_contract.delegate(encoded_zero_address, {"from": trp_recipient})
    # Check event and state
    assert unassign_tx.events["UnassignDelegate"]["voter"] == test_trp_escrow
    assert unassign_tx.events["UnassignDelegate"]["unassignedDelegate"] == delegate1
    assert contracts.voting.getDelegate(test_trp_escrow) == ZERO_ADDRESS
    assert list(contracts.voting.getDelegatedVoters(delegate1, 0, 3)) == []

    # A delegate can attempt to vote for a list of voters with a TRP participant
    voter = LDO_VOTE_EXECUTORS_FOR_TESTS[0]
    contracts.voting.assignDelegate(delegate1, {"from": accounts.at(voter, force=True)})
    assign_tx = trp_escrow_contract.delegate(encoded_delegate_address, {"from": trp_recipient})

    voters = [voter, test_trp_escrow]
    vote_for_tx = contracts.voting.attemptVoteForMultiple(vote_id, True, voters, {"from": delegate1})
    # Check events and state
    assert vote_for_tx.events.count("CastVote") == 2
    for index, voter in enumerate(voters):
        assert vote_for_tx.events["CastVote"][index]["voteId"] == vote_id
        assert vote_for_tx.events["CastVote"][index]["voter"] == voter
        assert vote_for_tx.events["CastVote"][index]["supports"] == True
    assert vote_for_tx.events["AttemptCastVoteAsDelegate"]["voteId"] == vote_id
    assert vote_for_tx.events["AttemptCastVoteAsDelegate"]["delegate"] == delegate1
    assert list(vote_for_tx.events["AttemptCastVoteAsDelegate"]["voters"]) == voters
    assert contracts.voting.getVoterState(vote_id, voters[0]) == VoterState.DelegateYea.value
    assert contracts.voting.getVoterState(vote_id, voters[1]) == VoterState.DelegateYea.value
    assert contracts.voting.getVote(vote_id)["yea"] == sum([contracts.ldo_token.balanceOf(v) for v in voters])


# TODO: finalize this test
# def test_delegation_deployed_trp_recipients(delegate1, trp_voting_adapter, test_vote):
#     w3 = Web3(Web3.HTTPProvider(f'https://{CHAIN_NETWORK_NAME}.infura.io/v3/{os.getenv("WEB3_INFURA_PROJECT_ID")}'))
#     factory_contract = w3.eth.contract(address=contracts.trp_escrow_factory.address, abi=contracts.trp_escrow_factory.abi)

#     logs = contracts.trp_escrow_factory.events.VestingEscrowCreated().get_logs(fromBlock=TRP_FACTORY_DEPLOY_BLOCK_NUMBER)
# event_signature_hash = w3.keccak(text="VestingEscrowCreated(address,address,address)").hex()
# deployed_trp_events = w3.eth.filter(
#     {"address": contracts.trp_escrow_factory.address, "fromBlock": TRP_FACTORY_DEPLOY_BLOCK_NUMBER, "topics": [event_signature_hash]}
# ).get_all_entries()
# decoded_events = _decode_logs(deployed_trp_events)["VestingEscrowCreated"]
# vote_id = test_vote[0]
# assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

# for trp_escrow in decoded_events:
#     recipient = trp_escrow["recipient"]
#     escrow = trp_escrow["escrow"]
#     escrow_contract = interface.Escrow(escrow)
#     encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(delegate1.address)
#     assign_tx = escrow_contract.delegate(encoded_delegate_address, {"from": recipient})
#     assert assign_tx.events["AssignDelegate"]["voter"] == escrow
#     assert assign_tx.events["AssignDelegate"]["assignedDelegate"] == delegate1
#     assert contracts.voting.getDelegate(escrow_contract) == delegate1

# delegated_voters = contracts.voting.getDelegatedVoters(delegate1, 0, decoded_events.)

# vote_before = contracts.voting.getVote(vote_id, {"from": delegate})
# assert vote_before["yea"] == 0
# if contracts.ldo_token.balanceOf(escrow) > 0:
#     contracts.voting.attemptVoteFor(vote_id, True, escrow, {"from": delegate})
#     vote_after = contracts.voting.getVote(vote_id, {"from": delegate})
#     assert vote_after["yea"] == contracts.ldo_token.balanceOf(escrow)
# else:
#     print(f"Escrow {escrow} has no LDO balance")

# encoded_zero_address = trp_voting_adapter.encode_delegate_calldata(ZERO_ADDRESS)

# reset_tx = escrow_contract.delegate(encoded_zero_address, {"from": recipient})
# assert contracts.voting.getDelegate(recipient) == ZERO_ADDRESS
# parsed_events = parse_reset_delegate_logs(reset_tx.logs)
# assert parsed_events[0]["voter"] == escrow
# assert parsed_events[0]["delegate"] == delegate
