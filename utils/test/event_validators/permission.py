from typing import NamedTuple, List
from web3 import Web3

from brownie.network.event import EventDict
from brownie import convert

from utils.permission_parameters import Param, encode_permission_params
from .common import validate_events_chain


class Permission(NamedTuple):
    entity: str
    app: str
    role: str


class PermissionP(NamedTuple):
    entity: str
    app: str
    role: str
    params: str


def validate_permission_create_event(event: EventDict, p: Permission, manager: str) -> None:
    _events_chain = ["LogScriptCall", "SetPermission", "ChangePermissionManager"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("SetPermission") == 1
    assert event.count("ChangePermissionManager") == 1

    assert event["SetPermission"]["entity"] == p.entity, "Wrong entity"
    assert event["SetPermission"]["app"] == p.app, "Wrong app address"
    assert event["SetPermission"]["role"] == p.role, "Wrong role"
    assert event["SetPermission"]["allowed"] is True, "Wrong role"

    assert event["ChangePermissionManager"]["app"] == p.app, "Wrong app address"
    assert event["ChangePermissionManager"]["role"] == p.role, "Wrong role"
    assert event["ChangePermissionManager"]["manager"] == manager, "Wrong manager"


def validate_permission_revoke_event(event: EventDict, p: Permission) -> None:
    _events_chain = ["LogScriptCall", "SetPermission"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("SetPermission") == 1

    assert event["SetPermission"]["entity"] == p.entity, "Wrong entity"
    assert event["SetPermission"]["app"] == p.app, "Wrong app address"
    assert event["SetPermission"]["role"] == p.role, "Wrong role"
    assert event["SetPermission"]["allowed"] is False, "Wrong role"


def validate_permission_grant_event(event: EventDict, p: Permission) -> None:
    _events_chain = ["LogScriptCall", "SetPermission"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("SetPermission") == 1

    assert event["SetPermission"]["entity"] == p.entity, "Wrong entity"
    assert event["SetPermission"]["app"] == p.app, "Wrong app address"
    assert event["SetPermission"]["role"] == p.role, "Wrong role"
    assert event["SetPermission"]["allowed"] is True, "Wrong allowed flag"


def validate_permission_grantp_event(event: EventDict, p: Permission, params: List[Param]) -> None:
    _events_chain = ["LogScriptCall", "SetPermission", "SetPermissionParams"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("SetPermission") == 1

    assert event["SetPermission"]["entity"] == p.entity, "Wrong entity"
    assert event["SetPermission"]["app"] == p.app, "Wrong app address"
    assert event["SetPermission"]["role"] == p.role, "Wrong role"
    assert event["SetPermission"]["allowed"] is True, "Wrong allowed flag"

    params_hash = Web3.solidity_keccak(["uint256[]"], [encode_permission_params(params)]).hex()

    assert event["SetPermissionParams"]["entity"] == p.entity, "Wrong entity"
    assert event["SetPermissionParams"]["app"] == p.app, "Wrong app address"
    assert event["SetPermissionParams"]["role"] == p.role, "Wrong role"
    assert event["SetPermissionParams"]["paramsHash"] == params_hash


def validate_grant_role_event(events: EventDict, role: str, grant_to: str, sender: str, emitted_by: str = None) -> None:
    # this event chain is actual if grant role is forvarded through
    _events_chain = ["LogScriptCall", "LogScriptCall", "RoleGranted", "ScriptResult"]

    validate_events_chain([e.name for e in events], _events_chain)

    assert events.count("RoleGranted") == 1

    assert events["RoleGranted"]["role"] == role, "Wrong role"
    assert events["RoleGranted"]["account"] == grant_to, "Wrong account"
    assert events["RoleGranted"]["sender"] == sender, "Wrong sender"
    if emitted_by is not None:
        assert convert.to_address(events["RoleGranted"]["_emitted_by"]) == convert.to_address(
            emitted_by
        ), "Wrong event emitter"


def validate_revoke_role_event(
    events: EventDict, role: str, revoke_from: str, sender: str, emitted_by: str = None
) -> None:
    _events_chain = ["LogScriptCall", "LogScriptCall", "RoleRevoked", "ScriptResult"]

    validate_events_chain([e.name for e in events], _events_chain)

    assert events.count("RoleRevoked") == 1

    assert events["RoleRevoked"]["role"] == role, "Wrong role"
    assert events["RoleRevoked"]["account"] == revoke_from, "Wrong account"
    assert events["RoleRevoked"]["sender"] == sender, "Wrong sender"

    if emitted_by is not None:
        assert convert.to_address(events["RoleRevoked"]["_emitted_by"]) == convert.to_address(emitted_by), "Wrong event emitter"


def validate_set_permission_manager_event(event: EventDict, app: str, role: str, manager: str) -> None:
    _events_chain = ["LogScriptCall", "ChangePermissionManager"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("ChangePermissionManager") == 1

    assert event["ChangePermissionManager"]["app"] == app, "Wrong app address"
    assert event["ChangePermissionManager"]["role"] == role, "Wrong role"
    assert event["ChangePermissionManager"]["manager"] == manager, "Wrong manager"


def validate_dg_permission_revoke_event(event: EventDict, p: Permission) -> None:
    _events_chain = ["LogScriptCall", "SetPermission", "ScriptResult", "Executed"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("SetPermission") == 1
    assert event.count("ScriptResult") == 1
    assert event.count("Executed") == 1

    assert event["SetPermission"]["entity"] == p.entity, "Wrong entity"
    assert event["SetPermission"]["app"] == p.app, "Wrong app address"
    assert event["SetPermission"]["role"] == p.role, "Wrong role"
    assert event["SetPermission"]["allowed"] is False, "Wrong role"
