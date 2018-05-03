"""Implementation of treadmill admin AWS subnet.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import metadata

from treadmill_aws import cli as aws_cli


def init():

    """AWS subnet CLI group"""
    formatter = cli.make_formatter('aws_subnet')

    @click.group()
    def subnet():
        """Manage subnet configuration"""
        pass

    @subnet.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List subnets"""
        ec2_conn = awscontext.GLOBAL.ec2
        subnets = ec2client.list_subnets(ec2_conn)
        cli.out(formatter(subnets))

    @subnet.command()
    @click.argument('subnet', required=False, type=aws_cli.SUBNET)
    @cli.admin.ON_EXCEPTIONS
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def configure(subnet):
        """Configure subnet"""
        ec2_conn = awscontext.GLOBAL.ec2
        if not subnet:
            subnet = {'ids': [metadata.subnet_id()]}

        subnet_obj = ec2client.get_subnet(ec2_conn, **subnet)
        cli.out(formatter(subnet_obj))

    del _list
    del configure

    return subnet
