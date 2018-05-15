"""Implementation of treadmill admin AWS user manager.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli
from treadmill_aws import usermanager


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
    @click.argument('username', required=True,
                    callback=aws_cli.sanitize_user_name)
    @click.option('--fname', required=True, help='First name/Proid name')
    @click.option('--lname', required=True, help='Last name/"proid"')
    @click.option('--utype', required=True,
                  type=click.Choice(['proid', 'user', 'privuser']),
                  help='Class of user')
    @cli.ON_CLI_EXCEPTIONS
    def configure(username, fname, lname, utype):
        """Create user.
        """
        ipa_client = awscontext.GLOBAL.ipaclient
        iam_conn = awscontext.GLOBAL.iam

        user = usermanager.create_user(ipa_client=ipa_client,
                                       iam_conn=iam_conn,
                                       user_name=username,
                                       first_name=fname,
                                       last_name=lname,
                                       user_type=utype)

        click.echo(user)

    @user.command(name='delete')
    @click.argument('username')
    @cli.ON_CLI_EXCEPTIONS
    def delete(username):
        """Delete user."""
        ipa_client = awscontext.GLOBAL.ipaclient
        iam_conn = awscontext.GLOBAL.iam

        usermanager.delete_user(ipa_client=ipa_client,
                                iam_conn=iam_conn,
                                user_name=username)

        click.echo(username)

    del _list
    del configure
    del delete

    return user
