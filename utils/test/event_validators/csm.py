from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_public_release_event(event: EventDict):
    _events_chain = ["LogScriptCall", "LogScriptCall", "PublicRelease", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("PublicRelease") == 1


def validate_set_key_removal_charge_event(
    event: EventDict,
    key_removal_charge: int,
):
    _events_chain = ["LogScriptCall", "LogScriptCall", "KeyRemovalChargeSet", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("KeyRemovalChargeSet") == 1
    assert event["KeyRemovalChargeSet"]["amount"] == key_removal_charge
