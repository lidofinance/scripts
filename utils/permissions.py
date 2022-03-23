from typing import Tuple, List
from utils.permission_parameters import Param, encode_permission_params

def create_permission(
    entity,
    target_app,
    permission_name,
    manager,
    acl
) -> Tuple[str, str]:
    permission_id = getattr(target_app, permission_name)()
    return acl.address, acl.createPermission.encode_input(entity, target_app, permission_id, manager)

def encode_permission_grant(
        target_app,
        permission_name: str,
        grant_to: str,
        acl
) -> Tuple[str, str]:
    permission_id = getattr(target_app, permission_name)()
    return acl.address, acl.grantPermission.encode_input(grant_to, target_app, permission_id)


def encode_permission_revoke(target_app, permission_name, revoke_from, acl) -> Tuple[str, str]:
    permission_id = getattr(target_app, permission_name)()
    return acl.address, acl.revokePermission.encode_input(revoke_from, target_app, permission_id)


def encode_permission_grant_p(
        target_app,
        permission_name: str,
        grant_to: str,
        acl,
        params: List[Param],
) -> Tuple[str, str]:
    permission_id = getattr(target_app, permission_name)()

    uint256_params = encode_permission_params(params)

    return acl.address, acl.grantPermissionP.encode_input(grant_to, target_app, permission_id, uint256_params)
