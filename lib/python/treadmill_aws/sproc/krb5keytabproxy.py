"""Local krb5-keytab proxy."""

import base64
import json
import logging
import os
import sys

import click
import dns.resolver

from twisted.internet import reactor
from twisted.internet import protocol
from twisted.internet import task

from treadmill import gssapiprotocol
from treadmill import fs
from treadmill import sysinfo
from treadmill import subproc
from treadmill import peercredprotocol

from treadmill_aws import awscontext


_LOGGER = logging.getLogger(__name__)

# Refresh tickets every 2 hours
_HOST_CREDS_REFRESH_INTERVAL = 60 * 60 * 2

_DEFAULT_SOCK_PATH = '/var/run/krb5keytab.sock'

_DEFAULT_KEYTAB_DIR = '/var/spool/keytabs'


def _request_keytab(server, port, principal):
    """Request keytab from keytab server."""
    client = gssapiprotocol.GSSAPILineClient(
        server, port, "host@%s" % server
    )

    client.connect()
    client.write(principal.encode("utf-8"))
    line = client.read().decode("utf-8")
    client.disconnect()

    return json.loads(line)


class Krb5KeytabProxy(peercredprotocol.PeerCredLineServer):
    """Proxy krb5keytab requests to krb5keytab server."""

    def __init__(self, hostname, domain, krb5keytab_servers, keytab_dir):
        self.hostname = hostname
        self.domain = domain
        self.krb5keytab_servers = krb5keytab_servers
        self.keytab_dir = keytab_dir
        super().__init__()

    def _handle_error(self, msg, err):
        """Handle error, return reason back to the client."""
        error = {
            'status': 'failure',
            'why': '{} - {}'.format(msg, str(err)),
        }
        self.write(json.dumps(error).encode('utf8'))

    def _handle(self, response):
        """Hanlde krb5keytab response.
        """
        try:
            _LOGGER.info('Got krb5keytab response: %s', response['status'])
            if response['status'] == 'success':
                self.write(json.dumps(response).encode('utf8'))
            else:
                # TODO: need better output for error messages.
                _LOGGER.error(
                    'Error requesting keytab: %s',
                    json.dumps(response, indent=4, sort_keys=True)
                )
                self.write(json.dumps(response).encode('utf8'))

        except Exception as err:  # pylint: disable=W0703
            self._handle_error('Unexpected error', err)
            raise err
        finally:
            self.transport.loseConnection()

    def _write_keytab(self, response):
        """Safely writes the keytab to disk."""
        keytab = os.path.join(self.keytab_dir, self.peer())
        keytab_entries = base64.standard_b64decode(
            response['result']['keytab_entries']
        )
        _LOGGER.info('Writing keytab: %s', keytab)
        fs.write_safe(
            keytab,
            lambda f: f.write(keytab_entries),
            owner=(self.uid, self.gid)
        )

    def got_line(self, data):
        """Process keytab request.

        data containes either target filename, in which case it will write the
        resulting keytab to the file, or "-", so that keytab will be returned
        to the client in the reply.
        """
        request = json.loads(data.decode())
        keytab = request.get('keytab')

        username = self.peer()
        principal = '{}/{}'.format(username, self.hostname)
        _LOGGER.info('Requesting keytab: %s', principal)

        endpoints = list(self.krb5keytab_servers)
        if not endpoints:
            # Try to get servers on each request, as srv records can change
            # during the run.
            try:
                srvrecs = dns.resolver.query(
                    '_ipakeytab._tcp.{}'.format(self.domain), 'SRV'
                )
            except dns.resolver.NXDOMAIN:
                srvrecs = []
            for result in srvrecs:
                _, _, port, server = result.to_text().split()
                endpoints.append('{}:{}'.format(server, port))

        last_err = None
        for endpoint in endpoints:
            _LOGGER.info('Connecting to %s', endpoint)
            server, port = endpoint.split(':')
            try:
                response = _request_keytab(server, int(port), principal)
                if response:
                    self._handle(response)
                    if keytab:
                        # Write keytab to the disk.
                        self._write_keytab(response)
                    break
            except ConnectionError as conn_err:
                last_err = conn_err
                _LOGGER.error(
                    'Error requesting keytab from %s - %s',
                    endpoint,
                    str(conn_err)
                )

        if last_err:
            self._handle_error('Error requesting keytabs', last_err)


class Krb5KeytabProxyFactory(protocol.Factory):
    """Krb5KeytabProxy protocol factory."""

    def __init__(self, krb5keytab_servers, keytab_dir):
        self.hostname = sysinfo.hostname()
        self.keytab_dir = keytab_dir
        self.domain = awscontext.GLOBAL.ipa_domain

        self.krb5keytab_servers = krb5keytab_servers

        super().__init__()

    def buildProtocol(self, addr):  # pylint: disable=C0103
        return Krb5KeytabProxy(
            hostname=self.hostname,
            domain=self.domain,
            krb5keytab_servers=self.krb5keytab_servers,
            keytab_dir=self.keytab_dir
        )


def init():
    """Top level command handler."""

    @click.command()
    @click.option('--krb5keytab-server',
                  required=False,
                  metavar='HOST:PORT',
                  multiple=True,
                  help='Address of ipakeytab server.')
    @click.option('--sock-path',
                  required=False,
                  help='Path to UDS socket server.')
    @click.option('--keytab-dir',
                  required=False,
                  help='Directory to store keytabs.')
    def krb5keytabproxy(sock_path, krb5keytab_server, keytab_dir):
        """Run krb5keytab proxy server."""
        if not sock_path:
            sock_path = _DEFAULT_SOCK_PATH

        if not keytab_dir:
            keytab_dir = _DEFAULT_KEYTAB_DIR

        # Check the keytab dir is owned by root.
        stat = os.stat(keytab_dir)
        if stat.st_uid != 0 or stat.st_gid != 0:
            _LOGGER.warning(
                'Keytab directory must be owned by root: %s', keytab_dir
            )
            sys.exit(-1)

        fs.rm_safe(sock_path)

        os.environ['KRB5CCNAME'] = 'FILE:/tmp/krb5cc_host_krb5keytab_proxy'

        def _refresh_krbcc():
            """Refresh host credentials."""
            subproc.check_call(['kinit', '-k'])

        task.LoopingCall(_refresh_krbcc).start(_HOST_CREDS_REFRESH_INTERVAL)
        reactor.listenUNIX(
            sock_path,
            Krb5KeytabProxyFactory(list(krb5keytab_server), keytab_dir)
        )
        reactor.run()

    return krb5keytabproxy
