"""Admin module to manage cell data.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill import admin
from treadmill import context
from treadmill import cli


_LOGGER = logging.getLogger(__name__)


def _set(data, name, value):
    """Safely set data attribute."""
    if not value:
        return False

    if value == '-':
        value = None
    data[name] = value
    return True


def init():
    """Admin Cell CLI module"""

    formatter = cli.make_formatter('aws_cell_data')

    @click.command(name='configure-data')
    @click.option('--docker-registries', help='Docker registries',
                  type=cli.LIST)
    @click.option('--image', help='Default AMI image.')
    # TODO: support XXXG as input.
    @click.option('--disk-size', help='Default image disk size.')
    @click.option('--size', help='Default instance size.')
    @click.option('--hostgroups', help='Nodes hostgroups.', type=cli.LIST)
    # TODO: should be list.
    @click.option('--secgroup', help='Nodes security group.')
    @click.option('--realm', help='Nodes kerberos realm.')
    @click.option('--instance-profile', help='Instance profile.')
    @click.option('--subnets', help='List of subnets.', type=cli.LIST)
    @click.option('--aws-account', help='AWS account.')
    @click.option('--aws-admin', help='AWS privileged user.')
    @click.option('--aws-region', help='AWS region.')
    @click.option('--s3-registry-bucket', help='S3 registry bucket name.')
    def configure_data_cmd(docker_registries,
                           image,
                           disk_size,
                           size,
                           hostgroups,
                           secgroup,
                           realm,
                           instance_profile,
                           subnets,
                           aws_account,
                           aws_admin,
                           aws_region,
                           s3_registry_bucket):
        """Configure cell data."""
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(context.GLOBAL.cell)
        data = cell.get('data', {})

        modified = _set(data, 'docker_registries', docker_registries)
        modified = _set(data, 'image', image) or modified
        modified = _set(data, 'disk_size', disk_size) or modified
        modified = _set(data, 'size', size) or modified
        modified = _set(data, 'hostgroups', hostgroups) or modified
        modified = _set(data, 'secgroup', secgroup) or modified
        modified = _set(data, 'realm', realm) or modified
        modified = _set(data, 'instance_profile', instance_profile) or modified
        modified = _set(data, 'subnets', subnets) or modified
        modified = _set(data, 'aws_account', aws_account) or modified
        modified = _set(data, 'aws_admin', aws_admin) or modified
        modified = _set(data, 'aws_region', aws_region) or modified
        modified = _set(data,
                        's3_registry_bucket',
                        s3_registry_bucket) or modified

        if modified:
            admin_cell.update(context.GLOBAL.cell, {'data': data})
        cli.out(formatter(data))

    return configure_data_cmd
