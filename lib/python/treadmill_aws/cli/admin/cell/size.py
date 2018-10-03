"""Admin module to manage cell instance size.
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

    @click.command(name='size')
    @click.option('--size', help='Instance size.')
    def size_cmd(size):
        """Configure cell instance size."""
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(context.GLOBAL.cell)
        data = cell.get('data', {})
        if size:
            data['size'] = size

        admin_cell.update(context.GLOBAL.cell, {'data': data})
        print(data.get('size', ''))

    return size_cmd
