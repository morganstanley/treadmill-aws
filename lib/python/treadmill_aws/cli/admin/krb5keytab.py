"""Request user or proid keytabs, directly contacting krb5keytab server.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import logging
import json
import errno
import io
import fcntl
import os
import pwd
import time

import click
import dns.resolver

import treadmill
from treadmill import sysinfo
from treadmill import fs
from treadmill import gssapiprotocol

from treadmill_aws import awscontext

_LOGGER = logging.getLogger(__name__)

_DEFAULT_KEYTAB_DIR = '/var/spool/keytabs'


def _cache_kt(cachedir, principal):
    """Replace / with # in principal name."""
    return os.path.join(cachedir, principal.replace('/', '#')) + '.keytab'


def _lock(lockdir, principal):
    """Create a file lock while processing keytab request."""
    lockfile = _cache_kt(lockdir, principal) + '.lock'
    lock = io.open(lockfile, 'w+')
    _LOGGER.debug('Locking: %s', lockfile)
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _LOGGER.debug('Locked.')
            return lock
        except IOError as err:
            if err.errno != errno.EAGAIN:
                raise
            time.sleep(0.1)


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


def _copy_keytab(kt_file, keytab, owner):
    """Copy keytab from cache."""
    try:
        pwnam = pwd.getpwnam(owner)
    except KeyError:
        _LOGGER.error('Invalid user: %s', owner)
        return

    with io.open(kt_file, 'rb') as kt:
        fs.write_safe(
            keytab,
            lambda f: f.write(kt.read()),
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
    @click.option('--cachedir',
                  required=False,
                  metavar='DIRECTORY',
                  help='Use local cache for keytabs.')
    @click.option('--lockdir',
                  required=False,
                  metavar='DIRECTORY',
                  default='/tmp',
                  help='Lock directory.')
    def krb5keytab(krb5keytab_server, principal, keytab, owner, cachedir,
                   lockdir):
        """krb5keytab client"""
        # pylint: disable=too-many-branches
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

        _LOGGER.info('Principal: %s', principal)
        _LOGGER.info('Keytab: %s', keytab)
        _LOGGER.info('Owner: %s', owner)
        kt_entries = None

        lock = None
        if lockdir != '-':
            # Obtain the lock and keep it open until app exits.
            lock = _lock(lockdir, principal)

        if cachedir:
            cache_kt = _cache_kt(cachedir, principal)
            if os.path.exists(cache_kt):
                _LOGGER.info('Copy cached keytab: %s', cache_kt)
                _copy_keytab(cache_kt, keytab, owner)
                return

        for endpoint in krb5keytab_server:
            _LOGGER.info('Connecting to %s', endpoint)
            server, port = endpoint.split(':')
            kt_entries = _request_keytab(server, int(port), principal)
            if kt_entries:
                if cachedir:
                    _write_keytab(kt_entries, cache_kt, 'root')

                _write_keytab(kt_entries, keytab, owner)
                return

    return krb5keytab
