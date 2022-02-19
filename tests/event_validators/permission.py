from typing import NamedTuple, List
from web3 import Web3

from brownie.network.event import EventDict

from utils.permission_parameters import Param, encode_permission_params
from .common import validate_events_chain


class Permission(NamedTuple):
    entity: str
    app: str
    role: str


def validate_permission_revoke_event(event: EventDict, p: Permission):
    _ldo_events_chain = ['LogScriptCall', 'SetPermission']

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count('SetPermission') == 1

    assert event['SetPermission']['entity'] == p.entity, "Wrong entity"
    assert event['SetPermission']['app'] == p.app, "Wrong app address"
    assert event['SetPermission']['role'] == p.role, "Wrong role"
    assert event['SetPermission']['allowed'] is False, "Wrong role"


def validate_permission_grantp_event(event: EventDict, p: Permission, params: List[Param]):
    _ldo_events_chain = ['LogScriptCall', 'SetPermission', 'SetPermissionParams']

    validate_events_chain([e.name for e in event], _ldo_events_chain)

    assert event.count('SetPermission') == 1

    assert event['SetPermission']['entity'] == p.entity, "Wrong entity"
    assert event['SetPermission']['app'] == p.app, "Wrong app address"
    assert event['SetPermission']['role'] == p.role, "Wrong role"
    assert event['SetPermission']['allowed'] is True, "Wrong allowed flag"

    params_hash = Web3.solidityKeccak(['uint256[]'], [encode_permission_params(params)]).hex()

    assert event['SetPermissionParams']['entity'] == p.entity, "Wrong entity"
    assert event['SetPermissionParams']['app'] == p.app, "Wrong app address"
    assert event['SetPermissionParams']['role'] == p.role, "Wrong role"
    assert event['SetPermissionParams']['paramsHash'] == params_hash
