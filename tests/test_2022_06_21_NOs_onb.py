"""
Tests for voting 21/06/2022.
"""
from collections import namedtuple

from utils.brownie_prelude import *

from brownie import accounts, reverts
from scripts.vote_2022_06_21_NOs_onb import start_vote  # , update_voting_app
from utils.test.tx_tracing_helpers import *
from utils.test.event_validators.node_operators_registry import (
    NodeOperatorItem,
    validate_node_operator_added_event,
)

NEW_NODE_OPERATORS = [
    # name, id, address
    # to get current id use Node Operators registry's getNodeOperatorsCount function
    # https://etherscan.io/address/0x55032650b14df07b85bF18A3a3eC8E0Af2e028d5#readProxyContract
    NodeOperatorItem(
        "RockLogic GmbH", 22, "0x49df3cca2670eb0d591146b16359fe336e476f29", 0
    ),
    NodeOperatorItem(
        "CryptoManufaktur", 23, "0x59eCf48345A221E0731E785ED79eD40d0A94E2A5", 0
    ),
    NodeOperatorItem(
        "Kukis Global", 24, "0x8845D7F2Bbfe82249c3B95e378A6eD039Dd953F5", 0
    ),
    NodeOperatorItem("Nethermind", 25, "0x237DeE529A47750bEcdFa8A59a1D766e3e7B5F91", 0),
]


def test_vote(ldo_holder, helpers, dao_voting, node_operators_registry):

    # Check that all NOs are unknown yet
    for node_operator in NEW_NODE_OPERATORS:
        with reverts("NODE_OPERATOR_NOT_FOUND"):
            no = node_operators_registry.getNodeOperator(node_operator.id, True)

    ##
    ## START VOTE
    ##
    vote_id = start_vote({"from": ldo_holder}, silent=True)[0]

    tx: TransactionReceipt = helpers.execute_vote(
        vote_id=vote_id, accounts=accounts, dao_voting=dao_voting
    )

    # Check that all NO was added
    for node_operator in NEW_NODE_OPERATORS:
        no = node_operators_registry.getNodeOperator(node_operator.id, True)

        message = f"Failed on {node_operator.name}"
        assert no[0] is True, message  # is active
        assert no[1] == node_operator.name, message  # name
        assert no[2] == node_operator.reward_address, message  # rewards address
        assert no[3] == 0  # staking limit

    # Validating events
    display_voting_events(tx)

    assert (
        count_vote_items_by_events(tx, dao_voting) == 4
    ), "Incorrect voting items count"

    evs = group_voting_events(tx)

    for i in range(0, 4):
        validate_node_operator_added_event(evs[i], NEW_NODE_OPERATORS[i])