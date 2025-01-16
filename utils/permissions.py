from typing import Tuple, List
from web3 import Web3

from brownie import convert, interface  # type: ignore
from utils.config import contracts
from utils.permission_parameters import Param, encode_permission_params


def encode_permission_create(entity, target_app, permission_name: str, manager) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = convert.to_uint(Web3.keccak(text=permission_name))
    return acl.address, acl.createPermission.encode_input(entity, target_app, permission_id, manager)


def encode_permission_grant(target_app, permission_name: str, grant_to: str) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = convert.to_uint(Web3.keccak(text=permission_name))
    return acl.address, acl.grantPermission.encode_input(grant_to, target_app, permission_id)


def encode_permission_revoke(target_app, permission_name, revoke_from) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = convert.to_uint(Web3.keccak(text=permission_name))
    return acl.address, acl.revokePermission.encode_input(revoke_from, target_app, permission_id)


def encode_permission_set_manager(target_app, permission_name: str, grant_to: str) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = convert.to_uint(Web3.keccak(text=permission_name))
    return acl.address, acl.setPermissionManager.encode_input(grant_to, target_app, permission_id)


def encode_permission_create(target_app, permission_name: str, grant_to, manager) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = convert.to_uint(Web3.keccak(text=permission_name))
    return acl.address, acl.createPermission.encode_input(grant_to, target_app, permission_id, manager)


def encode_permission_grant_p(
    target_app,
    permission_name: str,
    grant_to: str,
    params: List[Param],
) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = convert.to_uint(Web3.keccak(text=permission_name))

    uint256_params = encode_permission_params(params)

    return acl.address, acl.grantPermissionP.encode_input(grant_to, target_app, permission_id, uint256_params)


def encode_oz_grant_role(
    contract,
    role_name: str,
    grant_to: str,
) -> Tuple[str, str]:
    acl = interface.AccessControl(contract.address)
    role = convert.to_uint(Web3.keccak(text=role_name))

    return acl.address, acl.grantRole.encode_input(role, grant_to)


def encode_oz_revoke_role(
    contract,
    role_name: str,
    revoke_from: str,
) -> Tuple[str, str]:
    acl = interface.AccessControl(contract.address)
    role = convert.to_uint(Web3.keccak(text=role_name))

    return acl.address, acl.revokeRole.encode_input(role, revoke_from)
