""" Module defining interface to create/delete IAM roles.
"""

from treadmill_aws import iamclient


def _load_policy(policy_path):
    """Load policy from document and cast it to ASCII
       Click has already validated that the document exists and is readable
    """
    with open(policy_path, 'r') as file:
        policy = file.read()

    return policy.encode('ASCII')


def configure_role(iam_conn, role_name, role_type, policy_document):
    """Configure user role with AWS IAM.
    """
    loaded_policy = _load_policy(policy_path=policy_document)

    try:
        iam_role = iamclient.get_role(iam_conn=iam_conn, role_name=role_name)
    except iam_conn.exceptions.NoSuchEntityException:
        # If role does not exist:
        iam_role = iamclient.create_role(iam_conn=iam_conn,
                                         role_type=role_type,
                                         role_name=role_name,
                                         policy_document=loaded_policy)
    return iam_role


def delete_role(iam_conn, role_name):
    """Delete role from IAM.
    """
    try:
        iamclient.delete_role(iam_conn=iam_conn, role_name=role_name)
    except KeyError:
        pass
