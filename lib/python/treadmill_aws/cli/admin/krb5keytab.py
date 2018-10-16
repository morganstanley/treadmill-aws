"""Request user or proid keytabs, directly contacting krb5keytab server.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import json
import os
import pwd
import base64

import click
import dns.resolver

import treadmill
from treadmill import sysinfo
from treadmill import fs
from treadmill import gssapiprotocol

from treadmill_aws import awscontext

_LOGGER = logging.getLogger(__name__)

_DEFAULT_KEYTAB_DIR = '/var/spool/keytabs'


def _request_keytab(server, port, principal):
    """Request keytab from keytab server."""
    client = gssapiprotocol.GSSAPILineClient(
        server, port, "host@%s" % server
    )
    if not client.connect():
        _LOGGER.warning(
            'Failed to connect/authenticate to %s:%s',
            server, port
        )
        return None

    client.write(principal.encode("utf-8"))
    line = client.read().decode("utf-8")
    client.disconnect()

    response = json.loads(line)
    if response['status'] == 'failure':
        # TODO: need better output for error messages.
        _LOGGER.error(
            'Error requesting keytab: %s',
            json.dumps(response, indent=4, sort_keys=True)
        )
        return None

    if response['status'] == 'success':
        keytab_entries = base64.standard_b64decode(
            response['result']['keytab_entries']
        )

        return keytab_entries

    raise Exception(
        'Unexpected error: %s' %
        json.dumps(response, indent=4, sort_keys=True)
    )


def _write_keytab(keytab_entries, keytab, owner):
    """Write keytab file."""

    try:
        pwnam = pwd.getpwnam(owner)
    except KeyError:
        _LOGGER.error('Invalid user: %s', owner)
        return

    fs.write_safe(
        keytab,
        lambda f: f.write(keytab_entries),
        owner=(pwnam.pw_uid, pwnam.pw_gid)
    )


def init():
    """Admin Cell CLI module"""

    @click.command()
    @click.option('--krb5keytab-server',
                  required=False,
                  metavar='HOST:PORT',
                  multiple=True,
                  help='Address of ipakeytab server.')
    @click.option('--principal',
                  required=False,
                  help='Requsted principal ($user or $user/$hostname).')
    @click.option('--keytab',
                  required=False,
                  help='Destination keytab file.')
    @click.option('--owner',
                  required=False,
                  help='chown to specifed Unix ID.')
    def krb5keytab(krb5keytab_server, principal, keytab, owner):
        """krb5keytab client"""
        username = pwd.getpwuid(os.getuid())[0]
        hostname = sysinfo.hostname()

        treadmill.logging.set_log_level(logging.INFO)

        if not principal:
            principal = '{}/{}'.format(username, hostname)

        if not owner:
            owner = username

        if not keytab:
            keytab = os.path.join(_DEFAULT_KEYTAB_DIR, owner)

        if not krb5keytab_server:
            krb5keytab_server = []
            domain = awscontext.GLOBAL.ipa_domain
            try:
                srvrecs = dns.resolver.query(
                    '_ipakeytab._tcp.{}'.format(domain), 'SRV'
                )
            except dns.resolver.NXDOMAIN:
                srvrecs = []
            for result in srvrecs:
                _, _, port, server = result.to_text().split()
                krb5keytab_server.append('{}:{}'.format(server, port))

        if not krb5keytab_server:
            treadmill.cli.bad_exit(
                'Configuration/usage error: '
                '--krb5keytab-server not specified/DNS not configured'
                ' - exiting.'
            )

        _LOGGER.info('Principal   : %s', principal)
        _LOGGER.info('Keytab      : %s', keytab)
        _LOGGER.info('Owner       : %s', owner)
        kt_entries = None

        for endpoint in krb5keytab_server:
            _LOGGER.info('Connecting to %s', endpoint)
            server, port = endpoint.split(':')
            kt_entries = _request_keytab(server, int(port), principal)
            if kt_entries:
                _write_keytab(kt_entries, keytab, owner)
                return

    return krb5keytab
