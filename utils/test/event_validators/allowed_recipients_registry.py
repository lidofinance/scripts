from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_set_limit_parameter_event(
    event: EventDict, limit: int, period_duration_month: int, period_start_timestamp: int
):
    _events_chain = [
        "LogScriptCall",
        "LogScriptCall",
        "CurrentPeriodAdvanced",
        "LimitsParametersChanged",
        "ScriptResult",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("CurrentPeriodAdvanced") == 1
    assert event["CurrentPeriodAdvanced"]["_periodStartTimestamp"] == period_start_timestamp

    assert event.count("LimitsParametersChanged") == 1
    assert event["LimitsParametersChanged"]["_limit"] == limit
    assert event["LimitsParametersChanged"]["_periodDurationMonths"] == period_duration_month


def validate_update_spent_amount_event(
    event: EventDict,
    already_spent_amount: int,
    spendable_balance_in_period: int,
    period_start_timestamp: int,
    period_end_timestamp: int,
    is_period_advanced: bool = False,
):
    _events_chain = (
        ["LogScriptCall", "LogScriptCall", "CurrentPeriodAdvanced", "SpendableAmountChanged", "ScriptResult"]
        if is_period_advanced
        else ["LogScriptCall", "LogScriptCall", "SpendableAmountChanged", "ScriptResult"]
    )

    validate_events_chain([e.name for e in event], _events_chain)

    if is_period_advanced:
        assert event.count("CurrentPeriodAdvanced") == 1
        assert event["CurrentPeriodAdvanced"]["_periodStartTimestamp"] == period_start_timestamp

    assert event.count("SpendableAmountChanged") == 1
    assert event["SpendableAmountChanged"]["_alreadySpentAmount"] == already_spent_amount
    assert event["SpendableAmountChanged"]["_spendableBalance"] == spendable_balance_in_period
    assert event["SpendableAmountChanged"]["_spendableBalance"] == spendable_balance_in_period
    assert event["SpendableAmountChanged"]["_periodStartTimestamp"] == period_start_timestamp
    assert event["SpendableAmountChanged"]["_periodEndTimestamp"] == period_end_timestamp

def validate_set_spent_amount_event(
    event: EventDict,
    new_spent_amount: int,
):
    _events_chain = (
        ["LogScriptCall", "LogScriptCall", "SpentAmountChanged", "ScriptResult"]
    )

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("SpentAmountChanged") == 1
    assert event["SpentAmountChanged"]["_newSpentAmount"] == new_spent_amount
