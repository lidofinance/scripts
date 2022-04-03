from typing import Tuple, List

from utils.config import contracts
from utils.permission_parameters import Param, encode_permission_params

def encode_permission_create(
    entity,
    target_app,
    permission_name,
    manager
) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = getattr(target_app, permission_name)()
    return acl.address, acl.createPermission.encode_input(entity, target_app, permission_id, manager)

def encode_permission_grant(
        target_app,
        permission_name: str,
        grant_to: str
) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = getattr(target_app, permission_name)()
    return acl.address, acl.grantPermission.encode_input(grant_to, target_app, permission_id)


def encode_permission_revoke(target_app, permission_name, revoke_from) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = getattr(target_app, permission_name)()
    return acl.address, acl.revokePermission.encode_input(revoke_from, target_app, permission_id)


def encode_permission_grant_p(
        target_app,
        permission_name: str,
        grant_to: str,
        params: List[Param],
) -> Tuple[str, str]:
    acl = contracts.acl
    permission_id = getattr(target_app, permission_name)()

    uint256_params = encode_permission_params(params)

    return acl.address, acl.grantPermissionP.encode_input(grant_to, target_app, permission_id, uint256_params)
