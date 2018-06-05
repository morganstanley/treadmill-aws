"""Runs AWS credential service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill_aws import awscredential

_LOGGER = logging.getLogger(__name__)


def init():
    """Top level command handler."""

    @click.command()
    @click.option('--port',
                  required=True,
                  type=int,
                  help='Service port to listen on.')
    @click.option('--account-id',
                  required=True,
                  help='AWS Account ID.')
    @click.option('--realm',
                  required=True,
                  help='Kerberos realm of authorized users.')
    @click.option('--admin-group',
                  required=False,
                  help='Name of admin group (unix group).')
    def awscredentialserver(port, account_id, admin_group, realm):
        """Run AWS credential daemon."""
        awscredential.run_server(port, account_id, admin_group, realm)

    return awscredentialserver
