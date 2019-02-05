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
    """Safely set data attribute."""
    if not value:
        return False

    if value == '-':
        value = None
    data[name] = value
    return True


def init():
    """Admin Partition CLI module"""

    formatter = cli.make_formatter('aws_part_data')

    @click.command(name='configure-partition')
    @click.option('--autoscale-max', type=int,
                  help='Autoscaler maximum server count.')
    @click.option('--autoscale-min', type=int,
                  help='Autoscaler minimum server count.')
    @click.option('--app-ratio', type=float,
                  help='Autoscaler server-to-app ratio.')
    @click.argument('partition')
    def configure_partition_cmd(autoscale_max,
                                autoscale_min,
                                partition,
                                app_ratio):
        """Configure partition data."""
        cell = context.GLOBAL.cell
        admin_part = admin.Partition(context.GLOBAL.ldap.conn)

        try:
            part_data = admin_part.get([partition, cell], dirty=True)
            data = part_data.get('data', {})
        except ldap_exceptions.LDAPNoSuchObjectResult:
            data = {}

        autoscale = data.get('autoscale', {})
        if autoscale_max:
            autoscale['max_servers'] = autoscale_max
        if autoscale_min:
            autoscale['min_servers'] = autoscale_min
        if app_ratio:
            autoscale['server_app_ratio'] = app_ratio

        modified = _set(data, 'autoscale', autoscale)

        if modified:
            admin_part.update([partition, cell], {'data': data})

        cli.out(formatter(data))

    return configure_partition_cmd
