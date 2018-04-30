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

from treadmill_aws.cli import options


def init():

    """AWS subnet CLI group"""
    formatter = cli.make_formatter('aws_subnet')
    subnet_args = {}

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
    @options.make_subnet_opts(subnet_args)
    @cli.admin.ON_EXCEPTIONS
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def configure():
        """Configure subnet"""
        ec2_conn = awscontext.GLOBAL.ec2
        if subnet_args.get('tags', []):
            subnet = ec2client.get_subnet_by_tags(
                ec2_conn,
                subnet_args['tags']
            )
        else:
            subnet_id = subnet_args.get('id', metadata.subnet_id())
            subnet = ec2client.get_subnet_by_id(
                ec2_conn,
                subnet_id
            )

        cli.out(formatter(subnet))

    del _list
    del configure

    return subnet
