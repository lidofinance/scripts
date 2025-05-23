from brownie.network.event import EventDict
from .common import validate_events_chain
from brownie import convert


def validate_relay_allowed_list_manager_set(event: EventDict, new_manager: str, emitted_by: str | None = None):
    _events_chain = ["LogScriptCall", "LogScriptCall", "ManagerChanged", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ManagerChanged") == 1

    assert event["ManagerChanged"]["new_manager"] == new_manager
    if emitted_by is not None:
        event_emitted_by = convert.to_address(event["ManagerChanged"]["_emitted_by"])
        assert event_emitted_by == convert.to_address(
            emitted_by
        ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"
