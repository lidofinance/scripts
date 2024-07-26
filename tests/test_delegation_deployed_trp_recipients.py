import os

from brownie import accounts, chain, interface, ZERO_ADDRESS
from web3 import Web3

from utils.test.extra_data import VoterState
from utils.config import (
    LDO_HOLDER_ADDRESS_FOR_TESTS,
    contracts,
    TRP_FACTORY_DEPLOY_BLOCK_NUMBER,
    CHAIN_NETWORK_NAME,
)
from utils.voting import create_vote, bake_vote_items
from utils.import_current_votes import start_and_execute_votes


def create_dummy_vote(ldo_holder: str) -> int:
    vote_items = bake_vote_items(vote_desc_items=[], call_script_items=[])
    return create_vote(vote_items, {"from": ldo_holder}, cast_vote=False, executes_if_decided=False)[0]


def test_delegation_deployed_trp_recipients(delegate1, vote_ids_from_env, helpers, ldo_holder):
    if vote_ids_from_env:
        helpers.execute_votes(accounts, vote_ids_from_env, contracts.voting, topup="0.5 ether")
    else:
        start_and_execute_votes(contracts.voting, helpers)
    w3 = Web3(Web3.HTTPProvider(f'https://{CHAIN_NETWORK_NAME}.infura.io/v3/{os.getenv("WEB3_INFURA_PROJECT_ID")}'))

    factory_contract = w3.eth.contract(
        address=contracts.trp_escrow_factory.address, abi=contracts.trp_escrow_factory.abi
    )
    deployed_trp_events = factory_contract.events.VestingEscrowCreated().get_logs(
        fromBlock=TRP_FACTORY_DEPLOY_BLOCK_NUMBER
    )

    trp_voting_adapter_address = contracts.trp_escrow_factory.voting_adapter()
    trp_voting_adapter = interface.VotingAdapter(trp_voting_adapter_address)

    vote_id = create_dummy_vote(ldo_holder)
    assert contracts.voting.getVotePhase(vote_id) == 0  # Main phase
    vote = contracts.voting.getVote(vote_id)
    assert vote["yea"] == 0
    assert vote["nay"] == 0

    # Assign delegate to all deployed TRP recipients
    for event in deployed_trp_events:
        recipient = event["args"]["recipient"]
        escrow = event["args"]["escrow"]
        escrow_contract = interface.Escrow(escrow)
        encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(delegate1)
        assign_tx = escrow_contract.delegate(encoded_delegate_address, {"from": recipient})
        # Check events and state
        assert assign_tx.events["AssignDelegate"]["voter"] == escrow
        assert assign_tx.events["AssignDelegate"]["assignedDelegate"] == delegate1
        assert contracts.voting.getDelegate(escrow_contract) == delegate1
    deployed_trp_escrow_addresses = [event["args"]["escrow"] for event in deployed_trp_events]
    delegated_voters = contracts.voting.getDelegatedVoters(delegate1, 0, len(deployed_trp_escrow_addresses))
    assert delegated_voters == deployed_trp_escrow_addresses

    # Check vote state before voting
    vote = contracts.voting.getVote(vote_id)
    assert vote["yea"] == 0
    assert vote["nay"] == 0
    voters_state = contracts.voting.getVoterStateMultipleAtVote(vote_id, delegated_voters)
    for voter_state in voters_state:
        assert voter_state == VoterState.Absent.value

    # Filter zero balances
    delegated_voters = [v for v in delegated_voters if contracts.ldo_token.balanceOf(v) > 0]

    # Vote for all delegated voters
    vote_for_tx = contracts.voting.attemptVoteForMultiple(vote_id, True, delegated_voters, {"from": delegate1})
    # Check events and state
    assert vote_for_tx.events.count("CastVote") == len(delegated_voters)
    for index, voter in enumerate(delegated_voters):
        assert vote_for_tx.events["CastVote"][index]["voteId"] == vote_id
        assert vote_for_tx.events["CastVote"][index]["voter"] == voter
        assert vote_for_tx.events["CastVote"][index]["supports"] == True
    assert vote_for_tx.events["AttemptCastVoteAsDelegate"]["voteId"] == vote_id
    assert vote_for_tx.events["AttemptCastVoteAsDelegate"]["delegate"] == delegate1
    assert list(vote_for_tx.events["AttemptCastVoteAsDelegate"]["voters"]) == delegated_voters
    vote = contracts.voting.getVote(vote_id)
    assert vote["yea"] == sum([contracts.ldo_token.balanceOf(v) for v in delegated_voters])
    assert vote["nay"] == 0
    voters_state = contracts.voting.getVoterStateMultipleAtVote(vote_id, delegated_voters)
    for voter_state in voters_state:
        assert voter_state == VoterState.DelegateYea.value

    contracts.voting.vote(vote_id, True, False, {"from": LDO_HOLDER_ADDRESS_FOR_TESTS})
    # Fast-forward to the closed phase
    chain.sleep(contracts.voting.voteTime())
    chain.mine()
    assert contracts.voting.getVotePhase(vote_id) == 2  # Closed phase
    # Execute the vote
    execute_tx = contracts.voting.executeVote(vote_id, {"from": ldo_holder})
    assert execute_tx.events["ExecuteVote"]["voteId"] == vote_id

    # Unassign delegate from all deployed TRP recipients
    for event in deployed_trp_events:
        recipient = event["args"]["recipient"]
        escrow = event["args"]["escrow"]
        escrow_contract = interface.Escrow(escrow)
        encoded_delegate_address = trp_voting_adapter.encode_delegate_calldata(ZERO_ADDRESS)
        assign_tx = escrow_contract.delegate(encoded_delegate_address, {"from": recipient})
        # Check events and state
        assert assign_tx.events["UnassignDelegate"]["voter"] == escrow
        assert assign_tx.events["UnassignDelegate"]["unassignedDelegate"] == delegate1
        assert contracts.voting.getDelegate(escrow_contract) == ZERO_ADDRESS
    assert contracts.voting.getDelegatedVoters(delegate1, 0, len(deployed_trp_events)) == []
