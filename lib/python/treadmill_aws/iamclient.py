"""AWS IAM client helper function."""

from treadmill import exc


def create_user(iam_conn, user_name, path):
    """Create IAM user.
    """
    try:
        response = iam_conn.create_user(Path=path,
                                        UserName=user_name)

        return response['User']
    except iam_conn.exceptions.EntityAlreadyExistsException as err:
        raise exc.FoundError(str(err))


def delete_user(iam_conn, user_name):
    """Delete IAM user.
    """
    try:
        return iam_conn.delete_user(UserName=user_name)
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def list_users(iam_conn, path_prefix):
    """List IAM users.
    """
    response = iam_conn.list_users(PathPrefix=path_prefix)
    # TODO: handle errors.
    return response['Users']


def get_user(iam_conn, user_name):
    """Get IAM user information.
    """
    try:
        return iam_conn.get_user(UserName=user_name)['User']
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def put_user_policy(iam_conn, user_name, policy_name, policy_document):
    """Put user policy."""

    iam_conn.put_user_policy(
        UserName=user_name,
        PolicyName=policy_name,
        PolicyDocument=policy_document)


def delete_user_policy(iam_conn, user_name, policy_name):
    """Delete user policy."""

    iam_conn.delete_user_policy(
        UserName=user_name,
        PolicyName=policy_name)


def list_user_policies(iam_conn, user_name):
    """List user policies"""

    policies = []

    marker = None

    while True:
        if marker:
            response = iam_conn.list_user_policies(UserName=user_name,
                                                   Marker=marker)
        else:
            response = iam_conn.list_user_policies(UserName=user_name)
        for policy in response['PolicyNames']:
            policies.append(policy)
        if not response['IsTruncated']:
            break
        marker = response['Marker']

    return policies


def attach_user_policy(iam_conn, user_name, policy_arn):
    """Attach user policies"""
    try:
        return iam_conn.attach_user_policy(
            UserName=user_name,
            PolicyArn=policy_arn
        )
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def detach_user_policy(iam_conn, user_name, policy_arn):
    """Detach user policies"""

    try:
        return iam_conn.detach_user_policy(
            UserName=user_name,
            PolicyArn=policy_arn
        )
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def list_attached_user_policies(iam_conn, user_name):
    """List attached user policies"""

    policies = []

    marker = None

    while True:
        if marker:
            response = iam_conn.list_attached_user_policies(
                UserName=user_name, Marker=marker)
        else:
            response = iam_conn.list_attached_user_policies(UserName=user_name)
        for policy in response['AttachedPolicies']:
            policies.append(policy)
        if not response['IsTruncated']:
            break
        marker = response['Marker']

    return policies


def create_role(iam_conn,
                role_name,
                path,
                policy_document,
                max_session_duration=3600):
    """Create IAM role.
    """

    if not path:
        path = '/'

    try:
        response = iam_conn.create_role(
            Path=path,
            MaxSessionDuration=max_session_duration,
            RoleName=role_name,
            AssumeRolePolicyDocument=policy_document
        )
        return response['Role']
    except iam_conn.exceptions.EntityAlreadyExistsException as err:
        raise exc.FoundError(str(err))


def update_role(iam_conn, role_name, max_session_duration):
    """Update IAM role.
    """
    try:
        response = iam_conn.update_role(
            RoleName=role_name,
            MaxSessionDuration=max_session_duration
        )
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def delete_role(iam_conn, role_name):
    """Delete IAM role."""
    try:
        return iam_conn.delete_role(RoleName=role_name)
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def list_roles(iam_conn, path_prefix):
    """List roles."""
    response = iam_conn.list_roles(PathPrefix=path_prefix)
    # TODO: handle errors.
    return response['Roles']


def get_role(iam_conn, role_name):
    """Return role by name."""
    try:
        return iam_conn.get_role(RoleName=role_name)['Role']
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def update_assume_role_policy(iam_conn, role_name, policy_document):
    """Update assume role policy."""
    try:
        iam_conn.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=policy_document)
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def put_role_policy(iam_conn, role_name, policy_name, policy_document):
    """Put role policy."""

    iam_conn.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=policy_document)


def delete_role_policy(iam_conn, role_name, policy_name):
    """Delete role policy."""

    iam_conn.delete_role_policy(
        RoleName=role_name,
        PolicyName=policy_name)


def list_role_policies(iam_conn, role_name):
    """List role policies"""

    policies = []

    marker = None

    while True:
        if marker:
            response = iam_conn.list_role_policies(RoleName=role_name,
                                                   Marker=marker)
        else:
            response = iam_conn.list_role_policies(RoleName=role_name)
        for policy in response['PolicyNames']:
            policies.append(policy)
        if not response['IsTruncated']:
            break
        marker = response['Marker']

    return policies


def attach_role_policy(iam_conn, role_name, policy_arn):
    """Attach role policies"""
    try:
        return iam_conn.attach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def detach_role_policy(iam_conn, role_name, policy_arn):
    """Detach role policies"""

    try:
        return iam_conn.detach_role_policy(
            RoleName=role_name,
            PolicyArn=policy_arn
        )
    except iam_conn.exceptions.NoSuchEntityException as err:
        raise exc.NotFoundError(str(err))


def list_attached_role_policies(iam_conn, role_name):
    """List attached role policies"""

    policies = []

    marker = None

    while True:
        if marker:
            response = iam_conn.list_attached_role_policies(
                RoleName=role_name, Marker=marker)
        else:
            response = iam_conn.list_attached_role_policies(RoleName=role_name)
        for policy in response['AttachedPolicies']:
            policies.append(policy)
        if not response['IsTruncated']:
            break
        marker = response['Marker']

    return policies
