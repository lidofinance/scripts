from brownie.network.event import EventDict

from .common import validate_events_chain


def validate_time_constraints_executed_before_event(event: EventDict) -> None:
    _events_chain = ["LogScriptCall"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("LogScriptCall") == 1


def validate_dg_time_constraints_executed_before_event(event: EventDict) -> None:
    _events_chain = ["Executed"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("Executed") == 1


def validate_dg_time_constraints_executed_with_day_time_event(event: EventDict) -> None:
    _events_chain = ["Executed"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("Executed") == 1
