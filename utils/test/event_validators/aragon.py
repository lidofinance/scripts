from typing import Tuple, Annotated
from .common import validate_events_chain
from brownie.network.event import EventDict
from brownie import convert


def validate_push_to_repo_event(event: EventDict, semantic_version: Annotated[Tuple[int, int, int], 3]):
    _ldo_events_chain = ["LogScriptCall", "NewVersion"]

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count("NewVersion") == 1

    assert event["NewVersion"]["semanticVersion"] == semantic_version, "Wrong version"

def validate_aragon_grant_permission_event(
    event,
    entity: str,
    app: str,
    role: str,
    emitted_by: str,
) -> None:
    """
    Validate Aragon ACL SetPermission event for granting permission via DG proposal.
    Ensures only expected events are fired and all parameters are correct.
    """
    _events_chain = ["LogScriptCall", "SetPermission", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {event.count('LogScriptCall')}"
    assert event.count("SetPermission") == 1, f"Expected 1 SetPermission, got {event.count('SetPermission')}"
    assert event.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {event.count('ScriptResult')}"
    assert event.count("Executed") == 1, f"Expected 1 Executed, got {event.count('Executed')}"

    assert event["SetPermission"]["allowed"] is True, "Permission should be granted (allowed=True)"
    assert event["SetPermission"]["entity"] == entity, f"Wrong entity: expected {entity}, got {event['SetPermission']['entity']}"
    assert event["SetPermission"]["app"] == app, f"Wrong app: expected {app}, got {event['SetPermission']['app']}"
    assert event["SetPermission"]["role"] == role, f"Wrong role: expected {role}, got {event['SetPermission']['role']}"

    assert convert.to_address(event["SetPermission"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}"


def validate_aragon_revoke_permission_event(
    event,
    entity: str,
    app: str,
    role: str,
    emitted_by: str,
) -> None:
    """
    Validate Aragon ACL SetPermission event for revoking permission via DG proposal.
    Ensures only expected events are fired and all parameters are correct.
    """
    _events_chain = ["LogScriptCall", "SetPermission", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {event.count('LogScriptCall')}"
    assert event.count("SetPermission") == 1, f"Expected 1 SetPermission, got {event.count('SetPermission')}"
    assert event.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {event.count('ScriptResult')}"
    assert event.count("Executed") == 1, f"Expected 1 Executed, got {event.count('Executed')}"

    assert event["SetPermission"]["allowed"] is False, "Permission should be revoked (allowed=False)"
    assert event["SetPermission"]["entity"] == entity, f"Wrong entity: expected {entity}, got {event['SetPermission']['entity']}"
    assert event["SetPermission"]["app"] == app, f"Wrong app: expected {app}, got {event['SetPermission']['app']}"
    assert event["SetPermission"]["role"] == role, f"Wrong role: expected {role}, got {event['SetPermission']['role']}"

    assert convert.to_address(event["SetPermission"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}"


def validate_aragon_set_app_event(
    event,
    app_id: str,
    app: str,
    emitted_by: str,
) -> None:
    """
    Validate Aragon Kernel SetApp event via DG proposal.
    Ensures only expected events are fired and all parameters are correct.
    """
    _events_chain = ["LogScriptCall", "SetApp", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1, f"Expected 1 LogScriptCall, got {event.count('LogScriptCall')}"
    assert event.count("SetApp") == 1, f"Expected 1 SetApp, got {event.count('SetApp')}"
    assert event.count("ScriptResult") == 1, f"Expected 1 ScriptResult, got {event.count('ScriptResult')}"
    assert event.count("Executed") == 1, f"Expected 1 Executed, got {event.count('Executed')}"

    assert event["SetApp"]["appId"] == app_id, f"Wrong appId: expected {app_id}, got {event['SetApp']['appId']}"
    assert event["SetApp"]["app"] == app, f"Wrong app: expected {app}, got {event['SetApp']['app']}"

    assert convert.to_address(event["SetApp"]["_emitted_by"]) == convert.to_address(
        emitted_by
    ), f"Wrong event emitter: expected {emitted_by}"
