from brownie.network.event import EventDict

from .common import validate_events_chain


def validate_time_constraints_executed_before_event(event: EventDict, timestamp) -> None:
    _events_chain = ["LogScriptCall", "TimeBeforeTimestampChecked"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("LogScriptCall") == 1
    assert event.count("TimeBeforeTimestampChecked") == 1
    assert event["TimeBeforeTimestampChecked"][0]["timestamp"] == timestamp


def validate_dg_time_constraints_executed_before_event(event: EventDict, timestamp) -> None:
    _events_chain = ["TimeBeforeTimestampChecked", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("Executed") == 1
    assert event.count("TimeBeforeTimestampChecked") == 1
    assert event["TimeBeforeTimestampChecked"][0]["timestamp"] == timestamp


def validate_dg_time_constraints_executed_with_day_time_event(event: EventDict, start_day_time, end_day_time) -> None:
    _events_chain = ["TimeWithinDayTimeChecked", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("Executed") == 1
    assert event.count("TimeWithinDayTimeChecked") == 1
    assert event["TimeWithinDayTimeChecked"][0]["startDayTime"] == start_day_time
    assert event["TimeWithinDayTimeChecked"][0]["endDayTime"] == end_day_time
