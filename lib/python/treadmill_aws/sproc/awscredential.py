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
    @click.option('--accountid',
                  required=True,
                  help='AWS Account ID.')
    @click.option('--realm',
                  required=False,
                  help='Kerberos realm of authorized users.')
    @click.option('--adminprinc',
                  required=False,
                  help='Kerberos principal authorized for all.')
    def awscredentialserver(port, accountid, adminprinc, realm):
        """Run AWS credential daemon."""
        awscredential.run_server(port, accountid, adminprinc, realm)

    return awscredentialserver
