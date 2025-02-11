from brownie.network.event import EventDict
from .common import validate_events_chain

def validate_public_release_event(event: EventDict):
    _events_chain = ['LogScriptCall', 'LogScriptCall', 'PublicRelease', 'ScriptResult']
    validate_events_chain([e.name for e in event], _events_chain)
    assert event.count("PublicRelease") == 1
