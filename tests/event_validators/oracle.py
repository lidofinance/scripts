from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_beacon_report_receiver_set_event(event: EventDict, callback: str):
    _events_chain = ['LogScriptCall', 'BeaconReportReceiverSet']

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count('BeaconReportReceiverSet') == 1

    assert event['BeaconReportReceiverSet']['callback'] == callback