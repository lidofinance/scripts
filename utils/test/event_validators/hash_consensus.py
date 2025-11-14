from brownie.network.event import EventDict
from .common import validate_events_chain
from brownie import convert


def validate_hash_consensus_member_removed(event: EventDict, member: str, new_quorum: int, new_total_members: int, emitted_by: str = None, is_dg_event: bool = False):

    if is_dg_event:
        _events_chain = ["LogScriptCall", "LogScriptCall", "MemberRemoved", "ScriptResult", "Executed"]
    else:
        _events_chain = ["LogScriptCall", "LogScriptCall", "MemberRemoved", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("MemberRemoved") == 1

    assert event["MemberRemoved"]["addr"] == member
    assert event["MemberRemoved"]["newQuorum"] == new_quorum
    assert event["MemberRemoved"]["newTotalMembers"] == new_total_members

    event_emitted_by = convert.to_address(event["MemberRemoved"]["_emitted_by"])
    assert event_emitted_by == convert.to_address(
        emitted_by
    ),  f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"

def validate_hash_consensus_member_added(event: EventDict, member: str, new_quorum: int, new_total_members: int, emitted_by: str = None, is_dg_event: bool = False):
    if is_dg_event:
        _events_chain = ["LogScriptCall", "LogScriptCall", "MemberAdded", "ScriptResult", "Executed"]
    else:
        _events_chain =["LogScriptCall", "LogScriptCall", "MemberAdded", "ScriptResult"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("MemberAdded") == 1

    assert event["MemberAdded"]["addr"] == member
    assert event["MemberAdded"]["newQuorum"] == new_quorum
    assert event["MemberAdded"]["newTotalMembers"] == new_total_members

    event_emitted_by = convert.to_address(event["MemberAdded"]["_emitted_by"])
    assert event_emitted_by == convert.to_address(
        emitted_by
    ), f"Wrong event emitter {event_emitted_by} but expected {emitted_by}"
