from .common import validate_events_chain
from brownie.network.event import EventDict


def validate_change_vote_time_event(event: EventDict, vote_time: int):
    _ldo_events_chain = ['LogScriptCall', 'ChangeVoteTime']

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count('ChangeVoteTime') == 1

    assert event['ChangeVoteTime']['voteTime'] == vote_time, "Wrong voteTime"


def validate_change_objection_time_event(event: EventDict, objection_time: int):
    _ldo_events_chain = ['LogScriptCall', 'ChangeObjectionPhaseTime']

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count('ChangeObjectionPhaseTime') == 1

    assert event['ChangeObjectionPhaseTime']['objectionPhaseTime'] == objection_time, "Wrong voteTime"
