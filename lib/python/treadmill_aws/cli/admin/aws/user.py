"""Implementation of treadmill admin AWS user manager.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import json
import os

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli
from treadmill_aws import usermanager


def _default_policy():
    """Default role policy."""

    account = awscontext.GLOBAL.sts.get_caller_identity().get('Account')
    return {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Action': 'sts:AssumeRole',
                'Effect': 'Allow',
                'Principal': {
                    'AWS': 'arn:aws:iam::{}:root'.format(account),
                }
            }
        ],
    }


def init():
    """ AWS user CLI group"""
    formatter = cli.make_formatter('aws_user')

    @click.group()
    def user():
        """Manage user configuration"""
        pass

    @user.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List users.
        """
        ipa_client = awscontext.GLOBAL.ipaclient
        users = usermanager.list_users(ipa_client=ipa_client)
        cli.out(formatter(users))

    @user.command(name='configure')
    @click.option('--usertype', required=False,
                  type=click.Choice(['proid', 'user', 'privuser']),
                  help='User type.')
    @click.option('--fname', required=False,
                  help='First Name.')
    @click.option('--lname', required=False,
                  help='Last Name.')
    @click.option('--policy-doc', required=False,
                  help='IAM Role policy document.')
    @click.option('--kadmin', required=False,
                  help='IPA kadmin principal.')
    @click.option('--ktadmin', required=False,
                  help='IPA kadmin keytab file.')
    @click.argument('username', required=True,
                    callback=aws_cli.sanitize_user_name)
    @cli.admin.ON_EXCEPTIONS
    def configure(usertype, fname, lname, policy_doc, kadmin, ktadmin,
                  username):
        """Create user.
        """
        ipa_client = awscontext.GLOBAL.ipaclient
        iam_conn = awscontext.GLOBAL.iam
        if not kadmin:
            kadmin = os.getlogin()

        if not usertype:
            user = usermanager.get_user(ipa_client=ipa_client,
                                        iam_conn=iam_conn,
                                        user_name=username)
        else:
            if not policy_doc:
                policy = _default_policy()
            else:
                with io.open(policy) as f:
                    policy = json.loads(f.read())

            if not fname:
                fname = username
            if not lname:
                lname = username

            user = usermanager.create_user(
                ipa_client=ipa_client,
                iam_conn=iam_conn,
                kadmin=kadmin,
                ktadmin=ktadmin,
                user_name=username,
                first_name=fname,
                last_name=lname,
                user_type=usertype,
                policy=policy
            )

        cli.out(formatter(user))

    @user.command(name='delete')
    @click.argument('username')
    @cli.admin.ON_EXCEPTIONS
    def delete(username):
        """Delete user."""
        ipa_client = awscontext.GLOBAL.ipaclient
        iam_conn = awscontext.GLOBAL.iam
        usermanager.delete_user(ipa_client=ipa_client,
                                iam_conn=iam_conn,
                                user_name=username)

    del _list
    del configure
    del delete

    return user
