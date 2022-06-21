"""
Tests for voting vote_disable_testnet_validators.
"""

from event_validators.unpause import (
    validate_unpause_event
)

from tx_tracing_helpers import *

from scripts.vote_disable_testnet_validators import start_vote


def test_2022_04_16(ldo_holder, helpers, accounts, dao_voting, node_operators_registry, vote_id_from_env, bypass_events_decoding):

    #
    # START VOTE
    #
    vote_id = vote_id_from_env or start_vote({'from': ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, topup='0.5 ether'
    )
    # node_operators_registry.disableNodeOperator(20, {"from": accounts[0]})
    display_voting_events(tx)

    if bypass_events_decoding:
        return
