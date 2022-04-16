#!/usr/bin/python3

from typing import NamedTuple

from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_unpause_event(event: EventDict):
    # extra 'LogScriptCall' and 'ScriptResult' due to agent forwarding
    _unpause_events_chain = ['LogScriptCall', 'LogScriptCall', 'DepositsUnpaused', 'ScriptResult']

    validate_events_chain([e.name for e in event], _unpause_events_chain)

    assert event.count('DepositsUnpaused') == 1
