"""Runs IPA 525 credential service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill import sysinfo
from treadmill.syscall import krb5

from treadmill_aws import ipa525

_LOGGER = logging.getLogger(__name__)


def init():
    """Top level command handler."""

    @click.command()
    @click.option('--port',
                  envvar='IPA525_PORT',
                  required=True,
                  type=int,
                  help='Service port to listen on.')
    @click.option('--client-realm',
                  envvar='IPA525_CLIENT_REALM',
                  required=True,
                  multiple=True,
                  help='Client Kerberos realm.')
    @click.option('--server-realm',
                  envvar='IPA525_SERVER_REALM',
                  required=False,
                  help='Server Kerberos realm.')
    @click.option('-A', '--authz', help='Authoriztion server socket',
                  required=False,
                  envvar='IPA525_AUTHZ_SOCK')
    def ipa525server(port, client_realm, server_realm, authz):
        """Run IPA525 credential daemon."""
        if not server_realm:
            server_realm = krb5.get_host_realm(sysinfo.hostname())[0]

        ipa525.run_server(port, client_realm, server_realm, authz)

    return ipa525server
