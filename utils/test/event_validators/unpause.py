#!/usr/bin/python3

from typing import NamedTuple

from brownie.network.event import EventDict
from brownie import convert
from .common import validate_events_chain


def validate_unpause_event(event: EventDict):
    # extra 'LogScriptCall' and 'ScriptResult' due to agent forwarding
    _unpause_events_chain = ['LogScriptCall', 'LogScriptCall', 'DepositsUnpaused', 'ScriptResult']

    validate_events_chain([e.name for e in event], _unpause_events_chain)

    assert event.count('DepositsUnpaused') == 1


def validate_pause_for_event(events: EventDict, pause_for: int, sender: str, emitted_by: str):
    # extra 'LogScriptCall' and 'ScriptResult' due to agent forwarding
    _events_chain = ['LogScriptCall', 'LogScriptCall', 'Paused', 'ScriptResult', 'Executed']

    validate_events_chain([e.name for e in events], _events_chain)

    assert events.count("Paused") == 1

    assert events["Paused"]["duration"] == pause_for, "Wrong duration"

    assert convert.to_address(events["Paused"]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"
