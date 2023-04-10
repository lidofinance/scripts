from typing import NamedTuple, List
from web3 import Web3

from brownie.network.event import EventDict

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


def validate_permission_grant_event(event: EventDict, p: Permission) -> None:
    _events_chain = ["LogScriptCall", "SetPermission"]

    validate_events_chain([e.name for e in event], _events_chain)

    assert event.count("LogScriptCall") == 1
    assert event.count("SetPermission") == 1

    assert event["SetPermission"]["entity"] == p.entity, "Wrong entity"
    assert event["SetPermission"]["app"] == p.app, "Wrong app address"
    assert event["SetPermission"]["role"] == p.role, "Wrong role"
    assert event["SetPermission"]["allowed"] is True, "Wrong role"


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

    params_hash = Web3.solidityKeccak(["uint256[]"], [encode_permission_params(params)]).hex()

    assert event["SetPermissionParams"]["entity"] == p.entity, "Wrong entity"
    assert event["SetPermissionParams"]["app"] == p.app, "Wrong app address"
    assert event["SetPermissionParams"]["role"] == p.role, "Wrong role"
    assert event["SetPermissionParams"]["paramsHash"] == params_hash
