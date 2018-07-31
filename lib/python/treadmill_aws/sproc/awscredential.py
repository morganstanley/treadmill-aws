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
                  envvar='AWSCREDENTIAL_PORT',
                  required=True,
                  type=int,
                  help='Service port to listen on.')
    @click.option('--account-id',
                  envvar='AWSCREDENTIAL_ACCOUNT_ID',
                  required=True,
                  help='AWS Account ID.')
    @click.option('--realm',
                  envvar='AWSCREDENTIAL_REALM',
                  required=True,
                  help='Kerberos realm of authorized users.')
    @click.option('--admin-group',
                  envvar='AWSCREDENTIAL_ADMIN_GROUP',
                  required=False,
                  help='Name of admin group (unix group).')
    def awscredentialserver(port, account_id, admin_group, realm):
        """Run AWS credential daemon."""
        awscredential.run_server(port, account_id, admin_group, realm)

    return awscredentialserver
