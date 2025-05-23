from brownie.network.event import EventDict
from utils.test.event_validators.common import validate_events_chain
from brownie import convert

def validate_exited_validators_per_day_limit_event(event: EventDict, value: int, emitted_by: str | None = None):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "ExitedValidatorsPerDayLimitSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ExitedValidatorsPerDayLimitSet") == 1

    assert event["ExitedValidatorsPerDayLimitSet"]["exitedValidatorsPerDayLimit"] == value
    if emitted_by is not None:
        event_emitted_by = convert.to_address(event["ExitedValidatorsPerDayLimitSet"]["_emitted_by"])
        assert event_emitted_by == convert.to_address(
            emitted_by
        ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"

def validate_appeared_validators_limit_event(event: EventDict, value: int, emitted_by: str | None = None):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "AppearedValidatorsPerDayLimitSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("AppearedValidatorsPerDayLimitSet") == 1

    assert event["AppearedValidatorsPerDayLimitSet"]["appearedValidatorsPerDayLimit"] == value
    if emitted_by is not None:
        event_emitted_by = convert.to_address(event["AppearedValidatorsPerDayLimitSet"]["_emitted_by"])
        assert event_emitted_by == convert.to_address(
            emitted_by
        ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"

def validate_initial_slashing_and_penalties_event(event: EventDict, value: int, emitted_by: str | None = None):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "InitialSlashingAmountSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("InitialSlashingAmountSet") == 1

    assert event["InitialSlashingAmountSet"]["initialSlashingAmountPWei"] == value
    if emitted_by is not None:
        event_emitted_by = convert.to_address(event["InitialSlashingAmountSet"]["_emitted_by"])
        assert event_emitted_by == convert.to_address(
            emitted_by
        ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"