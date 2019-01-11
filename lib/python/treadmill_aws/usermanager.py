""" Module defining interface to create/delete/list freeIPA/AWS IAM users.
"""

import json
import subprocess

from treadmill import exc

from treadmill_aws import iamclient
from treadmill_aws import ipaclient


def get_ipa_user(ipa_client, user_name):
    """Get user details from IPA."""
    return ipa_client.show_user(user_name=user_name)


def get_iam_user(iam_conn, user_name):
    """Get IAM user details."""
    iam_user = iamclient.get_user(iam_conn=iam_conn, user_name=user_name)
    iam_role = iamclient.get_role(iam_conn=iam_conn, role_name=user_name)
    return {
        'user': iam_user,
        'role': iam_role,
    }


def create_ipa_user(ipa_client, kadmin, ktadmin, first_name,
                    last_name, user_name, user_type):
    """ Create user account with freeIPA if not already created.
    """
    try:
        # It is not possible to generate user with no password but with
        # random key using IPA api.
        #
        # Rather, we create IPA user with no password, and invoke kadmin
        # to generate the key in two separate steps.
        #
        # The "has_keytab" property is adjusted after successful invokation of
        # kadmin.
        ipa_user = ipa_client.add_user(
            user_name=user_name,
            first_name=first_name,
            last_name=last_name,
            user_type=user_type
        )

        if ktadmin:
            args = ['kadmin', '-p', kadmin, '-k', '-t', ktadmin, 'cpw',
                    '-randkey', user_name]
        else:
            # Invoking without ktadmin will cause kadmin to prompt for
            # password, so it is only appropriate in admin context (CLI), not
            # in server context.
            args = ['kadmin', '-p', kadmin, 'cpw', '-randkey', user_name]

        # TODO: replace with treadmill.subproc when aliases are available.
        subprocess.check_call(args)
        ipa_user['has_keytab'] = False
    except ipaclient.AlreadyExistsError as err:
        ipa_user = ipa_client.show_user(user_name=user_name)

    return ipa_user


def create_iam_user(iam_conn, user_name, policy):
    """ Create user account with AWS IAM if not already created.
    """
    try:
        iam_user = iamclient.get_user(iam_conn=iam_conn, user_name=user_name)
    except exc.NotFoundError:
        # If account does not exist:
        iam_user = iamclient.create_user(
            iam_conn=iam_conn,
            user_name=user_name,
            path='/'
        )

    try:
        iam_role = iamclient.get_role(iam_conn=iam_conn, role_name=user_name)
    except exc.NotFoundError:
        # If role does not exist:
        iam_role = iamclient.create_role(
            iam_conn=iam_conn,
            role_name=user_name,
            path='/',
            policy_document=json.dumps(policy)
        )

    return {
        'user': iam_user,
        'role': iam_role,
    }


def delete_ipa_user(iam_conn, user_name):
    """Delete user from FreeIPA if not already deleted.
    """
    try:
        iamclient.delete_user(iam_conn=iam_conn, user_name=user_name)
    except exc.NotFoundError:
        pass


def delete_iam_user(iam_conn, user_name):
    """Delete user from AWS IAM if not already deleted.
    """
    try:
        iamclient.delete_user(iam_conn=iam_conn, user_name=user_name)
    except exc.NotFoundError:
        pass

    try:
        iamclient.delete_role(iam_conn=iam_conn, role_name=user_name)
    except exc.NotFoundError:
        pass


def list_ipa_users(ipa_client, pattern=None):
    """Lists IPA users.
    """
    ipa_users = ipa_client.list_users(pattern)
    return ipa_users
