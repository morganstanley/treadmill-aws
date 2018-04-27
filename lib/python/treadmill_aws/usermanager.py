""" Module defining interface to create/delete/list freeIPA/AWS IAM users.
"""

import json
import subprocess

from treadmill import exc

from treadmill_aws import iamclient
from treadmill_aws import ipaclient


def _user(user):
    """Creates a top level user object, conflating IPA and AWS attributes."""
    user['id'] = user['_ipa']['uid'][0]
    user['type'] = user['_ipa'].get('userclass', [None])[0]
    return user


def get_user(iam_conn, ipa_client, user_name):
    """Get user details."""
    user = {
        '_ipa': None,
        '_iam': {
            'user': None,
            'role': None,
        }
    }
    ipa_user = ipa_client.show_user(user_name=user_name)
    iam_user = iamclient.get_user(iam_conn=iam_conn, user_name=user_name)
    iam_role = iamclient.get_role(iam_conn=iam_conn, role_name=user_name)
    user['_ipa'] = ipa_user
    user['_iam']['user'] = iam_user
    user['_iam']['role'] = iam_role
    return _user(user)


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


def create_iam_user(iam_conn, user_name):
    """ Create user account with AWS IAM if not already created.
    """
    try:
        iam_user = iamclient.get_user(iam_conn=iam_conn, user_name=user_name)
    except exc.NotFoundError:
        # If account does not exist:
        iam_user = iamclient.create_user(
            iam_conn=iam_conn,
            user_name=user_name,
        )

    return iam_user


def create_iam_role(iam_conn, role_name, policy):
    """Configure user role with AWS IAM.
    """
    try:
        iam_role = iamclient.get_role(iam_conn=iam_conn, role_name=role_name)
    except exc.NotFoundError:
        # If role does not exist:
        iam_role = iamclient.create_role(
            iam_conn=iam_conn,
            role_name=role_name,
            policy_document=json.dumps(policy)
        )
    return iam_role


def create_user(iam_conn, ipa_client, kadmin, ktadmin,
                user_name, first_name, last_name, user_type, policy):
    """ Create new user in freeIPA and in AWS IAM.
    """
    user = {
        '_ipa': None,
        '_iam': {
            'user': None,
            'role': None,
        }
    }
    ipa_user = create_ipa_user(
        ipa_client=ipa_client,
        kadmin=kadmin,
        ktadmin=ktadmin,
        first_name=first_name,
        last_name=last_name,
        user_name=user_name,
        user_type=user_type,
    )
    user['_ipa'] = ipa_user

    iam_user = create_iam_user(
        iam_conn=iam_conn,
        user_name=user_name,
    )
    user['_iam']['user'] = iam_user

    iam_role = create_iam_role(
        iam_conn=iam_conn,
        role_name=user_name,
        policy=policy
    )
    user['_iam']['role'] = iam_role
    return _user(user)


def delete_user(iam_conn, ipa_client, user_name):
    """Delete user from freeIPA and AWS IAM if not already deleted.
    """
    try:
        iamclient.delete_user(iam_conn=iam_conn, user_name=user_name)
    except exc.NotFoundError:
        pass

    try:
        iamclient.delete_role(iam_conn=iam_conn, role_name=user_name)
    except exc.NotFoundError:
        pass

    try:
        ipa_client.delete_user(user_name=user_name)
    except ipaclient.NotFoundError:
        pass


def list_users(ipa_client, pattern=None):
    """Lists users that exist in freeIPA.
    """
    ipa_users = ipa_client.list_users(pattern)

    # TODO: handle errors
    # TODO: need to query iam users and roles and potentially reconcile.
    users = [dict((['_ipa', ipa_user],)) for ipa_user in ipa_users]
    return [_user(user) for user in users]
