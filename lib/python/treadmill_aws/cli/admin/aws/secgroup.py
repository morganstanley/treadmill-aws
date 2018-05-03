"""Implementation of treadmill admin AWS security group.
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

    """AWS security group CLI group"""
    formatter = cli.make_formatter('aws_secgroup')

    @click.group()
    def secgroup():
        """Manage security group configuration."""
        pass

    @secgroup.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List security groups"""
        ec2_conn = awscontext.GLOBAL.ec2
        secgroups = ec2client.list_secgroups(ec2_conn)
        cli.out(formatter(secgroups))

    @secgroup.command()
    @click.argument('secgrp', required=False, type=aws_cli.SECGROUP)
    @cli.admin.ON_EXCEPTIONS
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def configure(secgrp):
        """Configure security group."""
        ec2_conn = awscontext.GLOBAL.ec2
        if not secgrp:
            secgrp = {'ids': [metadata.secgroup_id()]}

        grp_obj = ec2client.get_secgroup(ec2_conn, **secgrp)
        cli.out(formatter(grp_obj))

    del _list
    del configure

    return secgroup
