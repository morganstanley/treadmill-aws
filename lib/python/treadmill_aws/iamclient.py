"""AWS IAM client helper function."""


def create_user(iam_conn, user_name, user_type):
    """Create IAM user.
    """
    return iam_conn.create_user(Path='/{}/'.format(user_type),
                                UserName=user_name)


def delete_user(iam_conn, user_name):
    """Delete IAM user.
    """
    return iam_conn.delete_user(UserName=user_name)


def list_users(iam_conn, user_type=None):
    """List IAM users.
    """
    if user_type:
        return iam_conn.list_users(PathPrefix='/{}/'.format(user_type))
    else:
        return iam_conn.list_users()


def get_user(iam_conn, user_name):
    """Get IAM user information.
    """
    return iam_conn.get_user(UserName=user_name)


def create_role(iam_conn, role_name, role_type, policy_document):
    """Create IAM role.
    """
    return iam_conn.create_group(Path='/{}/'.format(role_type),
                                 RoleName=role_name,
                                 AssumeRolePolicyDocument=policy_document)


def delete_role(iam_conn, role_name):
    """Delete IAM role.
    """
    return iam_conn.delete_role(RoleName=role_name)


def list_roles(iam_conn, filters=None):
    """List roles."""
    if not filters:
        filters = []
    return iam_conn.list_roles().get('Roles', [])


def get_role(iam_conn, role_name):
    """Return role by name."""
    return iam_conn.get_role(RoleName=role_name)
