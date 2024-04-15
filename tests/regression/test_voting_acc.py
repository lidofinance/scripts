"""
Tests for lido staking limits
"""
from typing import Tuple, Optional

import pytest

# import os

# from web3 import Web3
from brownie import MockCallTarget, accounts, chain, reverts, interface, ZERO_ADDRESS, web3
from brownie.network.transaction import TransactionReceipt
from brownie.network.event import _decode_logs
from utils.voting import create_vote, bake_vote_items
from utils.config import LDO_VOTE_EXECUTORS_FOR_TESTS
from utils.evm_script import EMPTY_CALLSCRIPT
from utils.config import contracts, TRP_FACTORY_DEPLOY_BLOCK_NUMBER
import eth_abi


def filter_logs(logs, topic):
    return list(filter(lambda l: l["topics"][0] == topic, logs))


def parse_set_delegate_logs(logs):
    filtered_logs = filter_logs(logs, web3.keccak(text="SetDelegate(address,address)"))
    res = []
    for l in filtered_logs:
        res.append(
            {
                "voter": eth_abi.decode(["address"], l["topics"][1])[0],
                "delegate": eth_abi.decode(["address"], l["topics"][2])[0],
            }
        )
    return res


def parse_reset_delegate_logs(logs):
    filtered_logs = filter_logs(logs, web3.keccak(text="ResetDelegate(address,address)"))
    res = []
    for l in filtered_logs:
        res.append(
            {
                "voter": eth_abi.decode(["address"], l["topics"][1])[0],
                "delegate": eth_abi.decode(["address"], l["topics"][2])[0],
            }
        )
    return res


def parse_cast_vote_as_delegate_logs(logs):
    filtered_logs = filter_logs(logs, web3.keccak(text="CastVoteAsDelegate(uint256,address,address,bool,uint256)"))
    print(f"filtered_logs: {filtered_logs}")
    res = []
    for l in filtered_logs:
        res.append(
            {
                "voteId": eth_abi.decode(["uint256"], l["topics"][1])[0],
                "delegate": eth_abi.decode(["address"], l["topics"][2])[0],
                "voter": eth_abi.decode(["address"], l["topics"][3])[0],
            }
        )
    return res


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
        delegate_tx = contracts.voting.setDelegate(delegate, {"from": accounts.at(holder, force=True)})
        parsed_events = parse_set_delegate_logs(delegate_tx.logs)
        assert parsed_events[0]["voter"] == holder
        assert parsed_events[0]["delegate"] == delegate

    # [main] delegate vote for YEA holder 3 (reject not a delegation for holder 3)
    with reverts("VOTING_CAN_NOT_VOTE_FOR"):
        contracts.voting.attemptVoteFor(vote_id, True, holder3, {"from": delegate})

    # [main] delegate vote for YEA holders 1,2 (vote for 1 and 2)
    contracts.voting.attemptVoteFor(vote_id, True, holder1, {"from": delegate})
    vote_for_tx = contracts.voting.attemptVoteFor(vote_id, True, holder2, {"from": delegate})
    assert vote_for_tx.events["CastVote"]["voteId"] == vote_id
    assert vote_for_tx.events["CastVote"]["voter"] == holder2
    assert vote_for_tx.events["CastVote"]["supports"] == True

    parsed_cast_events = parse_cast_vote_as_delegate_logs(vote_for_tx.logs)

    assert parsed_cast_events[0]["voteId"] == vote_id
    assert parsed_cast_events[0]["delegate"] == delegate
    assert parsed_cast_events[0]["voter"] == holder2

    # [main] delegate re-vote for NAY holders 1,2
    contracts.voting.attemptVoteFor(vote_id, False, holder1, {"from": delegate})
    vote_for_tx = contracts.voting.attemptVoteFor(vote_id, False, holder2, {"from": delegate})
    assert vote_for_tx.events["CastVote"]["voteId"] == vote_id
    assert vote_for_tx.events["CastVote"]["voter"] == holder2
    assert vote_for_tx.events["CastVote"]["supports"] == False

    parsed_cast_events = parse_cast_vote_as_delegate_logs(vote_for_tx.logs)

    assert parsed_cast_events[0]["voteId"] == vote_id
    assert parsed_cast_events[0]["delegate"] == delegate
    assert parsed_cast_events[0]["voter"] == holder2

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
    reset_tx = contracts.voting.resetDelegate({"from": accounts.at(holder1, force=True)})
    parsed_events = parse_reset_delegate_logs(reset_tx.logs)
    assert parsed_events[0]["voter"] == holder1
    assert parsed_events[0]["delegate"] == delegate

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


def test_trp_delegation(test_trp_escrow, test_vote, delegate, trp_recipient, trp_voting_adapter):
    vote_id = test_vote[0]
    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

    encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(delegate.address)

    trp_escrow_contract = interface.Escrow(test_trp_escrow)

    delegate_tx = trp_escrow_contract.delegate(encoded_delegate_address, {"from": trp_recipient})
    parsed_events = parse_set_delegate_logs(delegate_tx.logs)
    assert parsed_events[0]["voter"] == test_trp_escrow
    assert parsed_events[0]["delegate"] == delegate

    delegated_voters = contracts.voting.getDelegatedVoters(delegate.address, 0, 5, {"from": delegate})
    assert delegated_voters[0] == [test_trp_escrow]
    assert contracts.voting.getDelegate(test_trp_escrow) == delegate

    vote_before = contracts.voting.getVote(vote_id, {"from": delegate})
    assert vote_before["yea"] == 0

    contracts.voting.attemptVoteFor(vote_id, True, test_trp_escrow, {"from": delegate})
    vote_after = contracts.voting.getVote(vote_id, {"from": delegate})
    assert vote_after["yea"] == 1_000_000_000_000_000_000

    encoded_zero_address = trp_voting_adapter.encode_delegate_calldata(ZERO_ADDRESS)

    reset_tx = trp_escrow_contract.delegate(encoded_zero_address, {"from": trp_recipient})
    assert contracts.voting.getDelegate(trp_recipient) == ZERO_ADDRESS
    parsed_events = parse_reset_delegate_logs(reset_tx.logs)
    assert parsed_events[0]["voter"] == test_trp_escrow
    assert parsed_events[0]["delegate"] == delegate


def test_trp_delegation_multiple(test_trp_escrow, test_vote, delegate, trp_recipient, trp_voting_adapter):
    vote_id = test_vote[0]
    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

    encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(delegate.address)

    interface.Escrow(test_trp_escrow).delegate(encoded_delegate_address, {"from": trp_recipient})

    delegated_voters = contracts.voting.getDelegatedVoters(delegate.address, 0, 5, {"from": delegate})
    assert delegated_voters[0] == [test_trp_escrow]
    assert contracts.voting.getDelegate(test_trp_escrow) == delegate

    vote_before = contracts.voting.getVote(vote_id, {"from": delegate})
    assert vote_before["yea"] == 0

    contracts.voting.attemptVoteForMultiple(vote_id, True, [test_trp_escrow], {"from": delegate})
    vote_after = contracts.voting.getVote(vote_id, {"from": delegate})
    assert vote_after["yea"] == 1_000_000_000_000_000_000


# TODO: finalize the test
# def test_deployed_trp_for_delegation(delegate, trp_voting_adapter, test_vote):
#     w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{os.getenv("WEB3_INFURA_PROJECT_ID")}'))

#     event_signature_hash = w3.keccak(text="VestingEscrowCreated(address,address,address)").hex()
#     deployed_trp_events = w3.eth.filter(
#         {"address": contracts.trp_escrow_factory.address, "fromBlock": TRP_FACTORY_DEPLOY_BLOCK_NUMBER, "topics": [event_signature_hash]}
#     ).get_all_entries()

#     decoded_events = _decode_logs(deployed_trp_events)["VestingEscrowCreated"]

#     vote_id = test_vote[0]
#     assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase

#     trp_escrow = decoded_events[0]
#     for trp_escrow in decoded_events:
#         recipient = trp_escrow["recipient"]
#         escrow = trp_escrow["escrow"]
#         escrow_contract = interface.Escrow(escrow)
#         encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(delegate.address)

#         delegate_tx = escrow_contract.delegate(encoded_delegate_address, {"from": recipient})
#         parsed_events = parse_set_delegate_logs(delegate_tx.logs)
#         assert parsed_events[0]["voter"] == escrow
#         assert parsed_events[0]["delegate"] == delegate

#         # vote_before = contracts.voting.getVote(vote_id, {"from": delegate})
#         # assert vote_before["yea"] == 0
#         # if contracts.ldo_token.balanceOf(escrow) > 0:
#         #     contracts.voting.attemptVoteFor(vote_id, True, escrow, {"from": delegate})
#         #     vote_after = contracts.voting.getVote(vote_id, {"from": delegate})
#         #     assert vote_after["yea"] == contracts.ldo_token.balanceOf(escrow)
#         # else:
#         #     print(f"Escrow {escrow} has no LDO balance")

#         # encoded_zero_address = trp_voting_adapter.encode_delegate_calldata(ZERO_ADDRESS)

#         # reset_tx = escrow_contract.delegate(encoded_zero_address, {"from": recipient})
#         # assert contracts.voting.getDelegate(recipient) == ZERO_ADDRESS
#         # parsed_events = parse_reset_delegate_logs(reset_tx.logs)
#         # assert parsed_events[0]["voter"] == escrow
#         # assert parsed_events[0]["delegate"] == delegate
