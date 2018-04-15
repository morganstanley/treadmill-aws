"""Implementation of treadmill admin EC2 subnet.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext


def init():

    """EC2 subnet CLI group"""
    formatter = cli.make_formatter('ec2_subnet')

    @click.group()
    def subnet():
        """Manage subnet configuration"""
        pass

    @subnet.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List subnets"""
        ec2_conn = awscontext.GLOBAL.ec2
        subnets = ec2_conn.describe_subnets().get('Subnets', [])
        cli.out(formatter(subnets))

    @subnet.command()
    @click.argument('subnet_id')
    @cli.admin.ON_EXCEPTIONS
    def configure(subnet_id):
        """Configure subnet"""
        ec2_conn = awscontext.GLOBAL.ec2
        subnet = ec2_conn.describe_subnets(
            SubnetIds=[subnet_id]
        )['Subnets'][0]
        cli.out(formatter(subnet))

    del _list
    del configure

    return subnet
