from brownie.network.event import EventDict
from .common import validate_events_chain

def validate_composite_receiver_callback_added_event(event: EventDict, callback: str, index: int):
    _events_chain = ['LogScriptCall', 'CallbackAdded']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('CallbackAdded') == 1

    assert event['CallbackAdded']['callback'] == callback
    assert event['CallbackAdded']['atIndex'] == index