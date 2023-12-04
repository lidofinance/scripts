"""
Tests for voting 12/12/2023

"""

from scripts.vote_2023_12_12 import start_vote
from brownie import interface
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.payout import Payout, validate_token_payout_event
from utils.test.event_validators.permission import Permission
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_name_set_event,
    NodeOperatorNameSetItem,
)
from utils.config import contracts, LDO_HOLDER_ADDRESS_FOR_TESTS, LIDO, AGENT

MANAGE_MEMBERS_AND_QUORUM_ROLE = "0x66a484cf1a3c6ef8dfd59d24824943d2853a29d96f34a01271efc55774452a51"


def test_vote(helpers, accounts, vote_ids_from_env):
    agent = contracts.agent

    assert not contracts.hash_consensus_for_accounting_oracle.hasRole(MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address)
    assert not contracts.hash_consensus_for_validators_exit_bus_oracle.hasRole(
        MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address
    )

    # START VOTE
    if len(vote_ids_from_env) > 0:
        (vote_id,) = vote_ids_from_env
    else:
        tx_params = {"from": LDO_HOLDER_ADDRESS_FOR_TESTS}
        vote_id, _ = start_vote(tx_params, silent=True)

    vote_tx = helpers.execute_vote(accounts, vote_id, contracts.voting)

    print(f"voteId = {vote_id}, gasUsed = {vote_tx.gas_used}")

    assert contracts.hash_consensus_for_accounting_oracle.hasRole(MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address)
    assert contracts.hash_consensus_for_validators_exit_bus_oracle.hasRole(
        MANAGE_MEMBERS_AND_QUORUM_ROLE, agent.address
    )
