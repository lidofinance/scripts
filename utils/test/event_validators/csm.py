from brownie.network.event import EventDict
from .common import validate_events_chain
from brownie import convert


def validate_public_release_event(event: EventDict):
    _events_chain = ["LogScriptCall", "LogScriptCall", "PublicRelease", "ScriptResult"]
    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("PublicRelease") == 1


def validate_set_key_removal_charge_event(
    event: EventDict,
    key_removal_charge: int,
    emitted_by: str | None = None,
    is_dg_event: bool = False,
):
    if is_dg_event:
        _events_chain = ["LogScriptCall", "LogScriptCall", "KeyRemovalChargeSet", "ScriptResult", "Executed"]
    else:
        _events_chain = ["LogScriptCall", "LogScriptCall", "KeyRemovalChargeSet", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("KeyRemovalChargeSet") == 1
    assert event["KeyRemovalChargeSet"]["amount"] == key_removal_charge

    event_emitted_by = convert.to_address(event["KeyRemovalChargeSet"]["_emitted_by"])
    assert event_emitted_by == convert.to_address(
        emitted_by
    ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"
