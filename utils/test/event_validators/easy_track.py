from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain
from brownie import convert


class EVMScriptFactoryAdded(NamedTuple):
    factory_addr: str
    permissions: str


def validate_evmscript_factory_added_event(
    event: EventDict,
    p: EVMScriptFactoryAdded,
    emitted_by: str,
):
    _events_chain=["LogScriptCall", "EVMScriptFactoryAdded"]
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("EVMScriptFactoryAdded") == 1

    assert event["EVMScriptFactoryAdded"]["_evmScriptFactory"] == p.factory_addr
    assert event["EVMScriptFactoryAdded"]["_permissions"] == p.permissions

    event_emitted_by = convert.to_address(event["EVMScriptFactoryAdded"]["_emitted_by"])
    assert event_emitted_by == convert.to_address(
        emitted_by
    ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"


def validate_evmscript_factory_removed_event(event: EventDict, factory_addr: str, emitted_by: str | None = None):
    _events_chain = ["LogScriptCall", "EVMScriptFactoryRemoved"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("EVMScriptFactoryRemoved") == 1

    assert event["EVMScriptFactoryRemoved"]["_evmScriptFactory"] == factory_addr

    event_emitted_by = convert.to_address(event["EVMScriptFactoryRemoved"]["_emitted_by"])
    assert event_emitted_by == convert.to_address(
        emitted_by
    ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"


def validate_motions_count_limit_changed_event(
    event: EventDict, motions_count_limit: int, emitted_by: str | None = None
):
    _events_chain = ["LogScriptCall", "MotionsCountLimitChanged"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("MotionsCountLimitChanged") == 1

    assert event["MotionsCountLimitChanged"]["_newMotionsCountLimit"] == motions_count_limit

    event_emitted_by = convert.to_address(event["MotionsCountLimitChanged"]["_emitted_by"])
    assert event_emitted_by == convert.to_address(
        emitted_by
    ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"
