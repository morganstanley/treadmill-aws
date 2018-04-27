"""AWS IAM client helper function."""

from treadmill import exc


def create_user(iam_conn, user_name):
    """Create IAM user.
    """
    try:
        response = iam_conn.create_user(Path='/',
                                        UserName=user_name)
        return response['User']
    except iam_conn.exceptions.EntityAlreadyExists as err:
        raise exc.FoundError(str(err))


def delete_user(iam_conn, user_name):
    """Delete IAM user.
    """
    try:
        return iam_conn.delete_user(UserName=user_name)
    except iam_conn.exceptions.NoSuchEntity as err:
        raise exc.NotFoundError(str(err))


def list_users(iam_conn, path_prefix=None):
    """List IAM users.
    """
    if not path_prefix:
        path_prefix = '/'
    response = iam_conn.list_users(PathPrefix=path_prefix)
    # TODO: handle errors.
    return response['Users']


def get_user(iam_conn, user_name):
    """Get IAM user information.
    """
    try:
        return iam_conn.get_user(UserName=user_name)['User']
    except iam_conn.exceptions.NoSuchEntity as err:
        raise exc.NotFoundError(str(err))


def create_role(iam_conn, role_name, policy_document):
    """Create IAM role.
    """
    try:
        response = iam_conn.create_role(
            Path='/',
            RoleName=role_name,
            AssumeRolePolicyDocument=policy_document
        )
        return response['Role']
    except iam_conn.exceptions.EntityAlreadyExists as err:
        raise exc.FoundError(str(err))


def delete_role(iam_conn, role_name):
    """Delete IAM role.
    """
    try:
        return iam_conn.delete_role(RoleName=role_name)
    except iam_conn.exceptions.NoSuchEntity as err:
        raise exc.NotFoundError(str(err))


def list_roles(iam_conn, path_prefix=None):
    """List roles."""
    if not path_prefix:
        path_prefix = '/'
    response = iam_conn.list_roles(PathPrefix=path_prefix)
    # TODO: handle errors.
    return response['Roles']


def get_role(iam_conn, role_name):
    """Return role by name."""
    try:
        return iam_conn.get_role(RoleName=role_name)['Role']
    except iam_conn.exceptions.NoSuchEntity as err:
        raise exc.NotFoundError(str(err))
