from typing import Tuple, List

from utils.config import (contracts, ldo_token_address)

def encode_permission_grant(
    target_app, permission_name: str, grant_to
) -> Tuple[str, str]:
    permission_id = getattr(target_app, permission_name)()
    acl = contracts.acl
    return (acl.address, acl.grantPermission.encode_input(grant_to, target_app, permission_id))

def encode_permission_grant_granular(
    target_app, permission_name: str, grant_to, acl_param: str
) -> Tuple[str, str]:
    permission_id = getattr(target_app, permission_name)()
    acl = contracts.acl
    return (acl.address, acl.grantPermissionP.encode_input(grant_to, target_app, permission_id, acl_param))

def encode_permission_revoke(
    target_app, permission_name: str, revoke_from
) -> Tuple[str, str]:
    permission_id = getattr(target_app, permission_name)()
    acl = contracts.acl
    return (acl.address, acl.revokePermission.encode_input(revoke_from, target_app, permission_id))

def require_first_param_is_addr(addr: str) -> List[str]:
    arg_id = '0x00' # arg 0
    op = '01'# operation eq (Op.Eq == 1)
    value = addr[2:].zfill(60) # pad 20bytes -> 30bytes, remove '0x'
    assert len(value) == (240 / 8) * 2, "incorrect length" # check the value length explicitly

    param_str = arg_id + op + value
    assert len(param_str) == (256 / 8) * 2 + 2, "incorrect length"

    return [param_str]
