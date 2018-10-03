"""Admin module to manage cell instance disk size.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill import admin
from treadmill import context


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.command(name='disk-size')
    @click.option('--disk-size', help='Instance disk-size.')
    def disk_size_cmd(disk_size):
        """Configure cell instance disk size."""
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(context.GLOBAL.cell)
        data = cell.get('data', {})
        if disk_size:
            data['disk_size'] = disk_size

        admin_cell.update(context.GLOBAL.cell, {'data': data})
        print(data.get('disk_size', ''))

    return disk_size_cmd
