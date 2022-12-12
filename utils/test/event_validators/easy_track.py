from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain


class EVMScriptFactoryAdded(NamedTuple):
    factory_addr: str
    permissions: str


def validate_evmscript_factory_added_event(event: EventDict, p: EVMScriptFactoryAdded):
    _events_chain = ["LogScriptCall", "EVMScriptFactoryAdded"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("EVMScriptFactoryAdded") == 1

    assert event["EVMScriptFactoryAdded"]["_evmScriptFactory"] == p.factory_addr
    assert event["EVMScriptFactoryAdded"]["_permissions"] == p.permissions


def validate_evmscript_factory_removed_event(event: EventDict, factory_addr: str):
    _events_chain = ["LogScriptCall", "EVMScriptFactoryRemoved"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("EVMScriptFactoryRemoved") == 1

    assert event["EVMScriptFactoryRemoved"]["_evmScriptFactory"] == factory_addr
