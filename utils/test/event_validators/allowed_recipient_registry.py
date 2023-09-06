from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain


class OwnershipTransferred(NamedTuple):
    previous_owner_addr: str
    new_owner_addr: str


def validate_limits_parameters_changed_event(event: EventDict, limit: int, period: int):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "CurrentPeriodAdvanced",
        "LimitsParametersChanged",
        "ScriptResult",
    ]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LimitsParametersChanged") == 1

    assert event["LimitsParametersChanged"]["_limit"] == limit
    assert event["LimitsParametersChanged"]["_periodDurationMonths"] == period


def validate_spent_amount_changed_event(event: EventDict, spent: int):
    _events_chain = ["LogScriptCall", "LogScriptCall", "SpentAmountChanged", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("SpentAmountChanged") == 1

    assert event["SpentAmountChanged"]["_newSpentAmount"] == spent
