""" Module defining interface to create/delete/list freeIPA/AWS IAM users.
"""

from treadmill_aws import iamclient


def create_ipa_user(ipa_client, first_name, last_name, user_name, user_type):
    """ Create user account with freeIPA if not already created.
    """
    try:
        ipa_user = ipa_client.show_user(user_name=user_name)
    except KeyError:
        # If account does not exist:
        ipa_user = ipa_client.add_user(user_name=user_name,
                                       first_name=first_name,
                                       last_name=last_name,
                                       user_type=user_type)
    return ipa_user


def create_iam_user(iam_conn, user_name, user_type):
    """ Create user account with AWS IAM if not already created.
    """
    try:
        iam_user = iamclient.get_user(iam_conn=iam_conn, user_name=user_name)
    except iam_conn.exceptions.NoSuchEntityException:
        # If account does not exist:
        iam_user = iamclient.create_user(iam_conn=iam_conn,
                                         user_name=user_name,
                                         user_type=user_type)
    return iam_user


def create_user(
        iam_conn, ipa_client, user_name, first_name, last_name, user_type):
    """ Create new user in freeIPA and in AWS IAM.
    """
    user = []
    ipa_user = create_ipa_user(ipa_client=ipa_client,
                               first_name=first_name,
                               last_name=last_name,
                               user_name=user_name,
                               user_type=user_type)
    user.append({'IPA': ipa_user['result']['result']})

    iam_user = create_iam_user(iam_conn=iam_conn,
                               user_name=user_name,
                               user_type=user_type)
    user.append({'IAM': iam_user['User']})

    return user


def delete_user(iam_conn, ipa_client, user_name):
    """Delete user from freeIPA and AWS IAM if not already deleted.
    """
    try:
        iamclient.delete_user(iam_conn=iam_conn, user_name=user_name)
    except iam_conn.exceptions.NoSuchEntityException:
        pass

    try:
        ipa_client.delete_user(user_name=user_name)
    except KeyError:
        pass


def list_users(ipa_client, pattern=None):
    """Lists users that exist in freeIPA.
    """
    return ipa_client.list_users(pattern)['result']['result']
