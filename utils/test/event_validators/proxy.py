from brownie import convert
from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_proxy_admin_changed(event: EventDict, prev_admin: str, new_admin: str, emitted_by: str) -> None:
    _events_chain = ["LogScriptCall", "AdminChanged"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("AdminChanged") == 1

    assert event["AdminChanged"]["previousAdmin"] == prev_admin, "Wrong previous admin"
    assert event["AdminChanged"]["newAdmin"] == new_admin, "Wrong new admin"

    assert convert.to_address(event["AdminChanged"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), "Wrong event emitter"


def validate_proxy_upgrade_event(event: EventDict, implementation: str, emitted_by: str):
    _events_chain = ["LogScriptCall", "Upgraded", "ScriptResult", "Executed"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("Upgraded") == 1

    assert "Upgraded" in event, "No Upgraded event found"

    assert event["Upgraded"][0]["implementation"] == implementation, "Wrong implementation address"

    assert convert.to_address(event["Upgraded"][0]["_emitted_by"]) == convert.to_address(
        emitted_by), "Wrong event emitter"
