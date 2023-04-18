"""
Tests for voting 18/04/2023.

"""
from scripts.vote_2023_04_18 import start_vote

from brownie.network.transaction import TransactionReceipt

from utils.config import network_name
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    validate_node_operator_staking_limit_set_event,
    NodeOperatorStakingLimitSetItem,
)

rockLogic_params_before = {
    "active": True,
    "name": 'RockLogic GmbH',
    "rewardAddress": '0x49df3cca2670eb0d591146b16359fe336e476f29',
    "stakingLimit": 9000,
}

rockLogic_params_after = {
    "active": True,
    "name": 'RockLogic GmbH',
    "rewardAddress": '0x49df3cca2670eb0d591146b16359fe336e476f29',
    "stakingLimit": 5800,
}

def check_no_params(no_params_from_registry, no_params_to_check):
    assert no_params_from_registry[0] == no_params_to_check["active"]
    assert no_params_from_registry[1] == no_params_to_check["name"]
    assert no_params_from_registry[2] == no_params_to_check["rewardAddress"]
    assert no_params_from_registry[3] == no_params_to_check["stakingLimit"]


def test_vote(
    helpers,
    accounts,
    vote_id_from_env,
    bypass_events_decoding,
    ldo_holder,
    dao_voting,
    node_operators_registry
):

    RockLogic_id = 22
    check_no_params(node_operators_registry.getNodeOperator(RockLogic_id, True), rockLogic_params_before)

    ##
    ## START VOTE
    ##
    vote_id = vote_id_from_env or start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting, skip_time=3 * 60 * 60 * 24
    )

    # 1. Set Staking limit for node operator RockLogic GmbH to 5800
    check_no_params(node_operators_registry.getNodeOperator(RockLogic_id, True), rockLogic_params_after)

    # validate vote events
    assert count_vote_items_by_events(tx, dao_voting) == 1, "Incorrect voting items count"

    display_voting_events(tx)

    if bypass_events_decoding or network_name() in ("goerli", "goerli-fork"):
        return

    evs = group_voting_events(tx)

    validate_node_operator_staking_limit_set_event(
        evs[0],
        NodeOperatorStakingLimitSetItem(
            id=22,
            staking_limit=rockLogic_params_after["stakingLimit"]
        )
    )
