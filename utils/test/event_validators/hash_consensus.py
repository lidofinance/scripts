from brownie.network.event import EventDict
from .common import validate_events_chain


def validate_hash_consensus_member_removed(event: EventDict, member: str, new_quorum: int, new_total_members: int):
    _events_chain = ["LogScriptCall", "LogScriptCall", "MemberRemoved", "ScriptResult"]

    print([e.name for e in event], _events_chain)
    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("MemberRemoved") == 1

    assert event["MemberRemoved"]["addr"] == member
    assert event["MemberRemoved"]["newQuorum"] == new_quorum
    assert event["MemberRemoved"]["newTotalMembers"] == new_total_members


def validate_hash_consensus_member_added(event: EventDict, member: str, new_quorum: int, new_total_members: int):
    _events_chain = ["LogScriptCall", "LogScriptCall", "MemberAdded", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("MemberAdded") == 1

    assert event["MemberAdded"]["addr"] == member
    assert event["MemberAdded"]["newQuorum"] == new_quorum
    assert event["MemberAdded"]["newTotalMembers"] == new_total_members
