from .common import validate_events_chain
from brownie.network.event import EventDict


def validate_change_vote_time_event(event: EventDict, voteTime: int):
    _ldo_events_chain = ['LogScriptCall', 'ChangeVoteTime']

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count('ChangeVoteTime') == 1

    assert event['ChangeVoteTime']['voteTime'] == voteTime, "Wrong voteTime"
