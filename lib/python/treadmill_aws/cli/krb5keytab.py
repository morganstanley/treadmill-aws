"""Request proid keytabs, directly contacting krb5keytab server.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import json
import base64

import click

from treadmill import cli
from treadmill import fs
from treadmill import peercredprotocol


_LOGGER = logging.getLogger(__name__)

_DEFAULT_KEYTAB_DIR = '/var/spool/keytabs'

_DEFAULT_SOCK_PATH = '/var/run/krb5keytab.sock'


def init():
    """Admin Cell CLI module"""

    @click.command()
    @click.option('--keytab',
                  required=False,
                  help='Keytab file.')
    @click.option('--sock-path',
                  required=False,
                  help='Path to krb5keytab socket.')
    def krb5keytab(keytab, sock_path):
        """The client utility to get krb5keytab from the local proxy."""
        if not sock_path:
            sock_path = _DEFAULT_SOCK_PATH

        client = peercredprotocol.PeerCredLineClient(sock_path)
        try:
            client.connect()
            request = {}
            if keytab:
                # If we write keytab ourselvs, do not ask server to write the
                # file.
                request['keytab'] = False

            client.write(json.dumps(request).encode('utf8'))
            reply = client.read()
            if not reply:
                cli.bad_exit('Connection closed.')

            response = json.loads(reply.decode())
            if response.get('status') != 'success':
                cli.bad_exit(response.get('why', 'Unknown error'))

            if keytab:
                keytab_entries = base64.standard_b64decode(
                    response['result']['keytab_entries']
                )
                _LOGGER.info('Writing keytab: %s', keytab)
                fs.write_safe(
                    keytab,
                    lambda f: f.write(keytab_entries),
                )

        except FileNotFoundError:
            cli.bad_exit(
                'Failed connecting to %s, krb5keytab proxy is not running.',
                sock_path
            )
        finally:
            client.disconnect()

    return krb5keytab
