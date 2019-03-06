"""Admin module to manage partition data.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click
from ldap3.core import exceptions as ldap_exceptions

from treadmill import admin
from treadmill import context
from treadmill import cli


_LOGGER = logging.getLogger(__name__)


def _set(data, name, value):
    """Safely set data attribute. Delete if user set attribute to '-'"""
    if not value:
        return False

    if value in ('-', ['-']):
        value = None
    data[name] = value
    return True


def init():
    """Admin Partition CLI module"""

    formatter = cli.make_formatter('aws_part_data')

    @click.command(name='configure-partition',
                   help='Pass "-" to revert attribute to cell default')
    @click.option('--autoscale-max', type=int,
                  help='Autoscaler maximum server count.')
    @click.option('--autoscale-min', type=int,
                  help='Autoscaler minimum server count.')
    @click.option('--app-ratio', type=float,
                  help='Autoscaler server-to-app ratio.')
    @click.option('--image', help='Default AMI image.')
    @click.option('--disk-size', help='Default image disk size.')
    @click.option('--size', help='Default instance size.')
    @click.option('--hostgroups', help='Node hostgroups.', type=cli.LIST)
    @click.option('--secgroup', help='Node security group.')
    @click.option('--instance-profile', help='Instance profile.')
    @click.option('--subnets', help='List of subnets.', type=cli.LIST)
    @click.option('--s3-registry-bucket', help='S3 registry bucket name.')
    @click.argument('partition')
    def configure_partition_cmd(autoscale_max,
                                autoscale_min,
                                app_ratio,
                                image,
                                disk_size,
                                size,
                                hostgroups,
                                secgroup,
                                instance_profile,
                                subnets,
                                s3_registry_bucket,
                                partition):
        """Configure partition data."""
        cell = context.GLOBAL.cell
        admin_part = admin.Partition(context.GLOBAL.ldap.conn)

        try:
            part_data = admin_part.get([partition, cell], dirty=True)
            data = part_data.get('data', {})
        except ldap_exceptions.LDAPNoSuchObjectResult:
            data = {}

        autoscale = data.get('autoscale', {})
        if autoscale_max is not None:
            autoscale['max_servers'] = autoscale_max
        if autoscale_min is not None:
            autoscale['min_servers'] = autoscale_min
        if app_ratio:
            autoscale['server_app_ratio'] = app_ratio

        modified = _set(data, 'autoscale', autoscale)
        modified = _set(data, 'image', image) or modified
        modified = _set(data, 'disk_size', disk_size) or modified
        modified = _set(data, 'size', size) or modified
        modified = _set(data, 'hostgroups', hostgroups) or modified
        modified = _set(data, 'secgroup', secgroup) or modified
        modified = _set(data, 'instance_profile', instance_profile) or modified
        modified = _set(data, 'subnets', subnets) or modified
        modified = _set(data,
                        's3_registry_bucket',
                        s3_registry_bucket) or modified

        if modified:
            admin_part.update([partition, cell], {'data': data})
        cli.out(formatter(data))

    return configure_partition_cmd
