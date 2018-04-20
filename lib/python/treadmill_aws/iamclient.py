"""AWS IAM client helper function."""


def list_roles(iam_conn, filters=None):
    """List vpcs."""
    if not filters:
        filters = []
    return iam_conn.list_roles().get('Roles', [])


def get_role(iam_conn, role_name):
    """Return role by name."""
    return iam_conn.get_role(RoleName=role_name)['Role']
