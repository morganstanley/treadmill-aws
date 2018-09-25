"""Admin module to manage cell Kerberos realm.
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

    @click.command(name='realm')
    @click.option('--realm', help='Kerberos realm.')
    def realm_cmd(realm):
        """Configure cell kerberos realm."""
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(context.GLOBAL.cell)
        data = cell.get('data', {})
        if realm:
            data['realm'] = realm

        admin_cell.update(context.GLOBAL.cell, {'data': data})
        print(data.get('realm', ''))

    return realm_cmd
