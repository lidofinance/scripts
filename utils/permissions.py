def encode_permission_grant(target_app, permission_name, grant_to, acl):
    permission_id = getattr(target_app, permission_name)()
    return (acl.address, acl.grantPermission.encode_input(grant_to, target_app, permission_id))


def encode_permission_revoke(target_app, permission_name, revoke_from, acl):
    permission_id = getattr(target_app, permission_name)()
    return (acl.address, acl.revokePermission.encode_input(revoke_from, target_app, permission_id))
