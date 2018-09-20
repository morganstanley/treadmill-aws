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
from treadmill import exc

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


def _ipa_grp(parent):
    """Configure IPA command group."""

    formatter = cli.make_formatter('ipa_user')

    @parent.group()
    def ipa():
        """Manage IPA user configuration"""
        pass

    @ipa.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def list_ipa():
        """List users.
        """
        ipa_client = awscontext.GLOBAL.ipaclient
        users = usermanager.list_users(ipa_client=ipa_client)
        cli.out(formatter(users))

    @ipa.command(name='configure')
    @click.option('--usertype', required=False,
                  type=click.Choice(['proid', 'user', 'privuser']),
                  help='User type.')
    @click.option('--fname', required=False,
                  help='First Name.')
    @click.option('--lname', required=False,
                  help='Last Name.')
    @click.option('--kadmin', required=False,
                  help='IPA kadmin principal.')
    @click.option('--ktadmin', required=False,
                  help='IPA kadmin keytab file.')
    @click.argument('username', required=True,
                    callback=aws_cli.sanitize_user_name)
    @cli.admin.ON_EXCEPTIONS
    def configure_ipa(usertype, fname, lname, kadmin, ktadmin, username):
        """Create user.
        """
        ipa_client = awscontext.GLOBAL.ipaclient
        if not kadmin:
            kadmin = os.getlogin()

        if not usertype:
            user = usermanager.get_ipa_user(ipa_client=ipa_client,
                                            user_name=username)
        else:
            if not fname:
                fname = username
            if not lname:
                lname = username

            user = usermanager.create_ipa_user(
                ipa_client=ipa_client,
                kadmin=kadmin,
                ktadmin=ktadmin,
                user_name=username,
                first_name=fname,
                last_name=lname,
                user_type=usertype,
            )

        cli.out(formatter(user))

    @ipa.command(name='delete')
    @click.argument('username')
    @cli.admin.ON_EXCEPTIONS
    def delete_ipa(username):
        """Delete IPA user."""
        ipa_client = awscontext.GLOBAL.ipaclient
        iam_conn = awscontext.GLOBAL.iam
        usermanager.delete_iam_user(iam_conn=iam_conn,
                                    user_name=username)

    del list_ipa
    del configure_ipa
    del delete_ipa


def _iam_grp(parent):
    """Configure IAM command group."""

    formatter = cli.make_formatter('aws_user')

    @parent.group()
    def iam():
        """Manage IAM user configuration"""
        pass

    @iam.command(name='configure')
    @click.option('--policy-doc', required=False,
                  help='IAM Role policy document.')
    @click.option('--create', is_flag=True, default=False,
                  help='Create IAM user/role.')
    @click.argument('username', required=True,
                    callback=aws_cli.sanitize_user_name)
    @cli.admin.ON_EXCEPTIONS
    def configure_iam(policy_doc, create, username):
        """Create IAM user.
        """
        iam_conn = awscontext.GLOBAL.iam
        try:
            user = usermanager.get_iam_user(iam_conn=iam_conn,
                                            user_name=username)
        except exc.NotFoundError:
            if not create:
                raise

        if create or policy_doc:
            policy = _default_policy()
            if policy_doc:
                with io.open(policy_doc) as f:
                    policy = json.loads(f.read())

            user = usermanager.create_iam_user(
                iam_conn=iam_conn,
                user_name=username,
                policy=policy
            )

        cli.out(formatter(user))

    @iam.command(name='delete')
    @click.argument('username')
    @cli.admin.ON_EXCEPTIONS
    def delete_iam(username):
        """Delete IAM user."""
        ipa_client = awscontext.GLOBAL.ipaclient
        iam_conn = awscontext.GLOBAL.iam
        usermanager.delete_iam_user(iam_conn=iam_conn,
                                    user_name=username)

    del configure_iam
    del delete_iam


def init():
    """ AWS user CLI group"""

    @click.group()
    def user():
        """Manage user configuration"""
        pass

    _ipa_grp(user)
    _iam_grp(user)

    return user
