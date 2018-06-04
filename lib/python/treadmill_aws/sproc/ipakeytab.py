"""Runs IPA keytab service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill_aws import ipakeytab

_LOGGER = logging.getLogger(__name__)


def init():
    """Top level command handler."""

    @click.command()
    @click.option('--port',
                  required=True,
                  type=int,
                  help='service port to listen on')
    @click.option('--realm',
                  required=True,
                  help='realm')
    @click.option('--admin-group',
                  required=False,
                  help='IPA Keytab admin group (unix group)')
    def ipakeytabserver(port, realm, admin_group):
        """Run IPA keytab daemon."""
        ipakeytab.run_server(port, realm, admin_group)

    return ipakeytabserver
