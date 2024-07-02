#!/usr/bin/python3

from typing import NamedTuple, Tuple

from brownie.convert.datatypes import ReturnValue
from brownie.network.event import EventDict
from .common import validate_events_chain


class StakingModuleItem(NamedTuple):
    id: int
    address: str | None
    name: str
    target_share: int
    module_fee: int
    treasury_fee: int


def validate_staking_module_added_event(event: EventDict, module_item: StakingModuleItem):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "StakingRouterETHDeposited",
        "StakingModuleAdded",
        "StakingModuleTargetShareSet",
        "StakingModuleFeesSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("StakingRouterETHDeposited") == 1
    assert event.count("StakingModuleAdded") == 1
    assert event.count("StakingModuleTargetShareSet") == 1
    assert event.count("StakingModuleFeesSet") == 1

    assert event["StakingRouterETHDeposited"]["stakingModuleId"] == module_item.id
    assert event["StakingRouterETHDeposited"]["amount"] == 0

    assert event["StakingModuleAdded"]["stakingModuleId"] == module_item.id
    assert event["StakingModuleAdded"]["stakingModule"] == module_item.address
    assert event["StakingModuleAdded"]["name"] == module_item.name

    assert event["StakingModuleTargetShareSet"]["stakingModuleId"] == module_item.id
    assert event["StakingModuleTargetShareSet"]["targetShare"] == module_item.target_share

    assert event["StakingModuleFeesSet"]["stakingModuleId"] == module_item.id
    assert event["StakingModuleFeesSet"]["stakingModuleFee"] == module_item.module_fee
    assert event["StakingModuleFeesSet"]["treasuryFee"] == module_item.treasury_fee


def validate_staking_module_update_event(event: EventDict, module_item: StakingModuleItem):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "StakingModuleTargetShareSet",
        "StakingModuleFeesSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("StakingModuleTargetShareSet") == 1
    assert event.count("StakingModuleFeesSet") == 1

    assert event["StakingModuleTargetShareSet"]["stakingModuleId"] == module_item.id
    assert event["StakingModuleTargetShareSet"]["targetShare"] == module_item.target_share

    assert event["StakingModuleFeesSet"]["stakingModuleId"] == module_item.id
    assert event["StakingModuleFeesSet"]["stakingModuleFee"] == module_item.module_fee
    assert event["StakingModuleFeesSet"]["treasuryFee"] == module_item.treasury_fee
