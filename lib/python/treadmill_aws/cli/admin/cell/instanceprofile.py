"""Admin module to manage cell AMIs.
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

    @click.command(name='instance-profile')
    @click.option('--instance-profile', help='instance-profile.')
    def instance_profile_cmd(instance_profile):
        """Configure default instance profile for cell nodes."""
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(context.GLOBAL.cell)
        data = cell.get('data', {})
        if instance_profile:
            data['instance_profile'] = instance_profile

        admin_cell.update(context.GLOBAL.cell, {'data': data})
        print(data.get('instance_profile', ''))

    return instance_profile_cmd
