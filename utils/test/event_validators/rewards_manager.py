from typing import NamedTuple

from brownie import convert
from brownie.network.event import EventDict
from .common import validate_events_chain

class OwnershipTransferred(NamedTuple):
    previous_owner_addr: str
    new_owner_addr: str

def validate_ownership_transferred_event(event: EventDict, ot: OwnershipTransferred, emitted_by: str = None):
    _events_chain = ['LogScriptCall', 'LogScriptCall', 'OwnershipTransferred', 'ScriptResult']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('OwnershipTransferred') == 1

    assert event['OwnershipTransferred']['previousOwner'] == ot.previous_owner_addr
    assert event['OwnershipTransferred']['newOwner'] == ot.new_owner_addr
    if emitted_by is not None:
        assert convert.to_address(event["OwnershipTransferred"]["_emitted_by"]) == convert.to_address(
            emitted_by
        ), "Wrong event emitter"
