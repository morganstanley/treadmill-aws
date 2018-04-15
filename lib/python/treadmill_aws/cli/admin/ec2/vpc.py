"""Implementation of treadmill admin EC2 vpc.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext


def init():

    """EC2 vpc CLI group"""
    formatter = cli.make_formatter('ec2_vpc')

    @click.group()
    def vpc():
        """Manage vpc configuration"""
        pass

    @vpc.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List vpcs"""
        ec2_conn = awscontext.GLOBAL.ec2
        vpcs = ec2_conn.describe_vpcs().get('Vpcs', [])
        cli.out(formatter(vpcs))

    @vpc.command()
    @click.argument('vpc_id')
    @cli.admin.ON_EXCEPTIONS
    def configure(vpc_id):
        """Configure vpc"""
        ec2_conn = awscontext.GLOBAL.ec2
        vpc = ec2_conn.describe_vpcs(
            VpcIds=[vpc_id]
        )['Vpcs'][0]
        cli.out(formatter(vpc))

    del _list
    del configure

    return vpc
