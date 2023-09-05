from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain

class TargetValidatorsCountChanged(NamedTuple):
    nodeOperatorId: int
    targetValidatorsCount: int

def validate_anchor_vault_implementation_upgrade_events(events: EventDict, implementation: str):
    _events_chain = ["LogScriptCall", "LogScriptCall", "Upgraded", "ScriptResult"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("Upgraded") == 1
    assert events["Upgraded"]["implementation"] == implementation, "Wrong anchor vault proxy implementation"

def validate_anchor_vault_version_upgrade_events(events: EventDict, new_version: str, new_emergency_admin: str):
    _events_chain = ["LogScriptCall", "LogScriptCall", "VersionIncremented", "EmergencyAdminChanged", "ScriptResult"]
    validate_events_chain([e.name for e in events], _events_chain)
    assert events.count("VersionIncremented") == 1
    assert events.count("EmergencyAdminChanged") == 1
    assert events["VersionIncremented"]["new_version"] == new_version, "Wrong anchor vault version"
    assert events["EmergencyAdminChanged"]["new_emergency_admin"] == new_emergency_admin, "Wrong anchor vault emergency admin"

