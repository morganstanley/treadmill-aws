"""Implementation of treadmill admin AWS role.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import iamclient


def init():
    """AWS IAM role CLI group"""
    formatter = cli.make_formatter('aws_role')

    @click.group()
    def role():
        """Manage IAM role configuration"""
        pass

    @role.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List roles"""
        iam_conn = awscontext.GLOBAL.iam
        roles = iamclient.list_roles(iam_conn)
        cli.out(formatter(roles))

    @role.command()
    @click.argument('role_name')
    @cli.admin.ON_EXCEPTIONS
    def configure(role_name):
        """Configure role"""
        iam_conn = awscontext.GLOBAL.iam
        role = iamclient.get_role(iam_conn, role_name)
        cli.out(formatter(role))

    del _list
    del configure

    return role
