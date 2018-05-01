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

from treadmill_aws.cli import options


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
    @click.argument(
        'secgrp',
        required=False,
        callback=options.parse_security_group()
    )
    @cli.admin.ON_EXCEPTIONS
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def configure(secgrp):
        """Configure security group."""
        ec2_conn = awscontext.GLOBAL.ec2
        if secgrp.get('tags', []):
            secgroup = ec2client.get_secgroup_by_tags(
                ec2_conn,
                secgrp['tags']
            )
        else:
            secgroup_id = secgrp.get('id', metadata.secgroup_id())
            secgroup = ec2client.get_secgroup_by_id(
                ec2_conn,
                secgroup_id
            )

        cli.out(formatter(secgroup))

    del _list
    del configure

    return secgroup
