from typing import NamedTuple

from brownie.network.event import EventDict
from brownie import ZERO_ADDRESS
from .common import validate_events_chain

class TargetValidatorsCountChanged(NamedTuple):
    nodeOperatorId: int
    targetValidatorsCount: int

def validate_anchor_vault_implementation_upgrade_events(events: EventDict, implementation: str, new_version: str):
    _events_chain = [
        "LogScriptCall", "LogScriptCall", "Upgraded", "VersionIncremented", "EmergencyAdminChanged", "BridgeConnectorUpdated",
        "RewardsLiquidatorUpdated", "InsuranceConnectorUpdated", "AnchorRewardsDistributorUpdated", "LiquidationConfigUpdated",
        "ScriptResult",
    ]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("Upgraded") == 1
    assert events["Upgraded"]["implementation"] == implementation, "Wrong anchor vault proxy implementation"

    assert events.count("VersionIncremented") == 1
    assert events.count("EmergencyAdminChanged") == 1
    assert events["VersionIncremented"]["new_version"] == new_version, "Wrong anchor vault version"
    assert events["EmergencyAdminChanged"]["new_emergency_admin"] == ZERO_ADDRESS, "Wrong anchor vault emergency admin"
    assert events["BridgeConnectorUpdated"]["bridge_connector"] == ZERO_ADDRESS, "Wrong anchor vault bridge connector"
    assert events["RewardsLiquidatorUpdated"]["rewards_liquidator"] == ZERO_ADDRESS, "Wrong anchor vault rewards liquidator"
    assert events["InsuranceConnectorUpdated"]["insurance_connector"] == ZERO_ADDRESS, "Wrong anchor vault insurance connector"
    assert events["LiquidationConfigUpdated"]["liquidations_admin"] == ZERO_ADDRESS, "Wrong anchor vault liquidations admin"
    assert events["LiquidationConfigUpdated"]["no_liquidation_interval"] == 0, "Wrong anchor vault no_liquidation_interval"
    assert events["LiquidationConfigUpdated"]["restricted_liquidation_interval"] == 0, "Wrong anchor vault restricted_liquidation_interval"
