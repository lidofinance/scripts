from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_relay_allowed_list_manager_set(event: EventDict, new_manager: str):
    _events_chain = ["LogScriptCall", "LogScriptCall", "ManagerChanged", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ManagerChanged") == 1

    assert event["ManagerChanged"]["new_manager"] == new_manager
