"""Implementation of treadmill admin EC2 vpc.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import ec2client


def init():

    """EC2 vpc CLI group"""
    formatter = cli.make_formatter('aws_vpc')

    @click.group()
    def vpc():
        """Manage vpc configuration"""
        pass

    @vpc.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List vpcs"""
        ec2_conn = awscontext.GLOBAL.ec2
        vpcs = ec2client.list_vpcs(ec2_conn)
        cli.out(formatter(vpcs))

    @vpc.command()
    @click.argument('vpc_id')
    @cli.admin.ON_EXCEPTIONS
    def configure(vpc_id):
        """Configure vpc"""
        ec2_conn = awscontext.GLOBAL.ec2
        vpc = ec2client.get_vpc_by_id(ec2_conn, vpc_id)
        cli.out(formatter(vpc))

    del _list
    del configure

    return vpc
