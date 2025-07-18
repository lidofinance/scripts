from typing import NamedTuple

from brownie.network.event import EventDict
from brownie import convert

from .common import validate_events_chain


class NodeOperatorItem(NamedTuple):
    name: str
    id: int
    reward_address: str
    staking_limit: int

class NodeOperatorStakingLimitSetItem(NamedTuple):
    id: int
    staking_limit: int

class NodeOperatorNameSetItem(NamedTuple):
    nodeOperatorId: int
    name: str

class NodeOperatorRewardAddressSetItem(NamedTuple):
    nodeOperatorId: int
    reward_address: str

class TargetValidatorsCountChanged(NamedTuple):
    nodeOperatorId: int
    targetValidatorsCount: int

def validate_node_operator_added_event(
    event: EventDict, node_operator_item: NodeOperatorItem
):
    _events_chain = ['LogScriptCall', 'LogScriptCall', 'NodeOperatorAdded', 'ScriptResult']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("NodeOperatorAdded") == 1

    assert event["NodeOperatorAdded"]["nodeOperatorId"] == node_operator_item.id
    assert event["NodeOperatorAdded"]["name"] == node_operator_item.name
    assert (
        event["NodeOperatorAdded"]["rewardAddress"] == node_operator_item.reward_address
    )
    assert (
        event["NodeOperatorAdded"]["stakingLimit"] == node_operator_item.staking_limit
    )

def validate_node_operator_staking_limit_set_event(
    event: EventDict, node_operator_staking_limit_item: NodeOperatorStakingLimitSetItem
):
    _events_chain = ["LogScriptCall", "KeysOpIndexSet", "NodeOperatorStakingLimitSet"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("NodeOperatorStakingLimitSet") == 1

    assert event["NodeOperatorStakingLimitSet"]["id"] == node_operator_staking_limit_item.id
    assert event["NodeOperatorStakingLimitSet"]["stakingLimit"] == node_operator_staking_limit_item.staking_limit


def validate_node_operator_name_set_event(
    event: EventDict, node_operator_name_item: NodeOperatorNameSetItem, emitted_by: str = None, is_dg_event=False
):
    if is_dg_event:
        _events_chain = ["LogScriptCall", "LogScriptCall", "NodeOperatorNameSet", "ScriptResult", "Executed"]
    else:
        _events_chain = ["LogScriptCall", "LogScriptCall", "NodeOperatorNameSet", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("NodeOperatorNameSet") == 1

    assert event["NodeOperatorNameSet"]["nodeOperatorId"] == node_operator_name_item.nodeOperatorId
    assert event["NodeOperatorNameSet"]["name"] == node_operator_name_item.name

    if emitted_by is not None:
        assert convert.to_address(event["NodeOperatorNameSet"]["_emitted_by"]) == convert.to_address(
            emitted_by
        ), "Wrong event emitter"

def validate_node_operator_reward_address_set_event(
    event: EventDict, node_operator_reward_address_item: NodeOperatorRewardAddressSetItem, emitted_by: str = None, is_dg_event=False
):
    if is_dg_event:
        _events_chain = ["LogScriptCall", "LogScriptCall", "NodeOperatorRewardAddressSet", "ScriptResult", "Executed"]
    else:
        _events_chain = ["LogScriptCall", "LogScriptCall", "NodeOperatorRewardAddressSet", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("NodeOperatorRewardAddressSet") == 1

    assert event["NodeOperatorRewardAddressSet"]["nodeOperatorId"] == node_operator_reward_address_item.nodeOperatorId
    assert event["NodeOperatorRewardAddressSet"]["rewardAddress"] == node_operator_reward_address_item.reward_address

    if emitted_by is not None:
        assert convert.to_address(event["NodeOperatorRewardAddressSet"]["_emitted_by"]) == convert.to_address(
            emitted_by
        ), "Wrong event emitter"

def validate_target_validators_count_changed_event(event: EventDict, t: TargetValidatorsCountChanged):
    _events_chain = ["LogScriptCall", "LogScriptCall", "TargetValidatorsCountChanged", "KeysOpIndexSet", "NonceChanged", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("TargetValidatorsCountChanged") == 1

    assert event["TargetValidatorsCountChanged"]["nodeOperatorId"] == t.nodeOperatorId
    assert event["TargetValidatorsCountChanged"]["targetValidatorsCount"] == t.targetValidatorsCount

def validate_node_operator_deactivated(event: EventDict, node_operator_id: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "NodeOperatorActiveSet",
        "KeysOpIndexSet",
        "NonceChanged",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("NodeOperatorActiveSet") == 1

    assert event["NodeOperatorActiveSet"]["nodeOperatorId"] == node_operator_id
    assert not event["NodeOperatorActiveSet"]["active"]
