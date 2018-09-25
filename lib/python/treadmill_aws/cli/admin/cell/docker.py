"""Admin module to manage cell Docker registries.
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

    @click.command(name='docker')
    @click.option('--add', multiple=True, help='Docker registry to add.')
    @click.option('--remove', multiple=True, help='Docker registry to remove.')
    def docker(add, remove):
        """Configure cell docker registries."""
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(context.GLOBAL.cell)
        data = cell.get('data', {})
        registries = set(data.get('docker_registries', []))

        for registry in add:
            registries.add(registry)
        for registry in remove:
            registries.discard(registry)

        data['docker_registries'] = list(registries)
        admin_cell.update(context.GLOBAL.cell, {'data': data})

        for registry in registries:
            print(registry)

    return docker
