from brownie.network.event import EventDict
from .common import validate_events_chain
from brownie import convert


def validate_add_token_event(
    event: EventDict, token: str, emitted_by: str | None = None
):
    _events_chain = [
        "LogScriptCall",
        "TokenAdded",
    ]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("TokenAdded") == 1
    
    assert event["TokenAdded"]["_token"] == convert.to_address(
        token
    ), f"Wrong token address {event['TokenAdded']['_token']} but expected {token}"

    event_emitted_by = convert.to_address(event["TokenAdded"]["_emitted_by"])
    assert event_emitted_by == convert.to_address(
        emitted_by
    ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"
