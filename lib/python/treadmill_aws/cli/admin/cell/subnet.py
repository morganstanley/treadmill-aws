"""Admin module to manage cell subnets.
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

    @click.command(name='subnet')
    @click.option('--add', multiple=True, help='Subnet to add.')
    @click.option('--remove', multiple=True, help='Subnet to remove.')
    def subnet_cmd(add, remove):
        """Configure cell subnets."""
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(context.GLOBAL.cell)
        data = cell.get('data', {})
        subnets = set(data.get('subnets', []))

        for subnet in add:
            subnets.add(subnet)
        for subnet in remove:
            subnets.discard(subnet)

        data['subnets'] = list(subnets)
        admin_cell.update(context.GLOBAL.cell, {'data': data})

        for subnet in subnets:
            print(subnet)

    return subnet_cmd
