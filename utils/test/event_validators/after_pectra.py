from brownie.network.event import EventDict
from utils.config import (
    AGENT,
)
from utils.test.event_validators.permission import validate_grant_role_event, validate_revoke_role_event
from utils.test.event_validators.common import validate_events_chain

# Roles
EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE = "0x60b9982471bc0620c7b74959f48a86c55c92c11876fddc5b0b54d1ec47153e5d"
APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE = "0x14ca7b84baa11a976283347b0159b8ddf2dcf5fd5cf613cc567a3423cf510119"
INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE = "0xebfa317a5d279811b024586b17a50f48924bce86f6293b233927322d7209b507"


def validate_sc_exited_validators_limit_update(events: list[EventDict], exitedValidatorsPerDayLimit):
    validate_grant_role_event(
        events[0],
        EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_exited_validators_per_day_limit_event(events[1], exitedValidatorsPerDayLimit)
    validate_revoke_role_event(
        events[2],
        EXITED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )


def validate_appeared_validators_limit_update(events: list[EventDict], appearedValidatorsPerDayLimit):
    validate_grant_role_event(
        events[0],
        APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_appeared_validators_limit_event(events[1], appearedValidatorsPerDayLimit)
    validate_revoke_role_event(
        events[2],
        APPEARED_VALIDATORS_PER_DAY_LIMIT_MANAGER_ROLE,
        AGENT,
        AGENT,
    )


def validate_initial_slashing_and_penalties_update(events: list[EventDict], initialSlashingAmountPWei):
    validate_grant_role_event(
        events[0],
        INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE,
        AGENT,
        AGENT,
    )
    validate_initial_slashing_and_penalties_event(events[1], initialSlashingAmountPWei)
    validate_revoke_role_event(
        events[2],
        INITIAL_SLASHING_AND_PENALTIES_MANAGER_ROLE,
        AGENT,
        AGENT,
    )


def validate_exited_validators_per_day_limit_event(event: EventDict, value: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "ExitedValidatorsPerDayLimitSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("ExitedValidatorsPerDayLimitSet") == 1

    assert event["ExitedValidatorsPerDayLimitSet"]["exitedValidatorsPerDayLimit"] == value


def validate_appeared_validators_limit_event(event: EventDict, value: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "AppearedValidatorsPerDayLimitSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("AppearedValidatorsPerDayLimitSet") == 1

    assert event["AppearedValidatorsPerDayLimitSet"]["appearedValidatorsPerDayLimit"] == value


def validate_initial_slashing_and_penalties_event(event: EventDict, value: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "InitialSlashingAmountSet",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("InitialSlashingAmountSet") == 1

    assert event["InitialSlashingAmountSet"]["initialSlashingAmountPWei"] == value
