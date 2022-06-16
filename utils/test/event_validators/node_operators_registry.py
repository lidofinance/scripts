from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain


class NodeOperatorItem(NamedTuple):
    name: str
    id: int
    reward_address: str
    staking_limit: int


def validate_node_operator_added_event(
    event: EventDict, node_operator_item: NodeOperatorItem
):
    _events_chain = ["LogScriptCall", "NodeOperatorAdded"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("NodeOperatorAdded") == 1

    assert event["NodeOperatorAdded"]["id"] == node_operator_item.id
    assert event["NodeOperatorAdded"]["name"] == node_operator_item.name
    assert (
        event["NodeOperatorAdded"]["rewardAddress"] == node_operator_item.reward_address
    )
    assert (
        event["NodeOperatorAdded"]["stakingLimit"] == node_operator_item.staking_limit
    )
