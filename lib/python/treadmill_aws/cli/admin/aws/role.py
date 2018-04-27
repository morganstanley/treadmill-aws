"""Implementation of treadmill admin AWS role management.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import iamclient
from treadmill_aws import rolemanager


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
        roles = iamclient.list_roles(iam_conn=iam_conn)
        cli.out(formatter(roles))

    @role.command(name='configure')
    @click.option('--rname', required=True, help='Role Name')
    @click.option('--utype', required=True, help='Role Type')
    @click.option('--policy_doc', required=True,
                  type=click.Path(exists=True,
                                  readable=True),
                  help='Path to policy JSON file')
    @cli.admin.ON_EXCEPTIONS
    def configure(rname, utype, policy_doc):
        """Configure role"""
        iam_conn = awscontext.GLOBAL.iam

        role = rolemanager.configure_role(iam_conn=iam_conn,
                                          role_name=rname,
                                          role_type=utype,
                                          policy_document=policy_doc)

        click.echo(role)

    @role.command(name='delete')
    @click.argument('name')
    @cli.ON_CLI_EXCEPTIONS
    def delete(name):
        """Delete role."""
        iam_conn = awscontext.GLOBAL.iam

        rolemanager.delete_role(iam_conn=iam_conn,
                                role_name=name)

        click.echo(name)

    del _list
    del configure
    del delete

    return role
