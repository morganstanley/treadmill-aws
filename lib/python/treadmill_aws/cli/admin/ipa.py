"""Admin IPA.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

import treadmill
from treadmill import cli

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli


_LOGGER = logging.getLogger(__name__)

DEFAULT_WEIGHT = 10
DEFAULT_PRIORITY = 10

# TODO: consider moving these constants to ipaclient.
_CLI_EXCEPTIONS = [
    (treadmill_aws.ipaclient.AuthenticationError, None),
]


def _get_state(ipaclient, idnsname):
    """Return set of currently defined SRV records."""
    current = set()
    result = ipaclient.get_dns_record(idnsname)['result']['result']
    for item in result:
        for record in item.get('srvrecord', []):
            _w, _p, port, host = record.split()
            current.add('{}:{}'.format(host.rstrip('.'), port))
    return current


def _set_state(ipaclient, idnsname, add, remove):
    """Add/remove SRV records."""
    current = _get_state(ipaclient, idnsname)

    missing = set(add) - current
    extra = current & set(remove)

    if not (missing or extra):
        return current
    else:
        for endpoint in missing:
            host, port = endpoint.split(':')
            ipaclient.add_srv_record(idnsname, host, port)

        for endpoint in extra:
            host, port = endpoint.split(':')
            ipaclient.delete_srv_record(idnsname, host, port)

        return _get_state(ipaclient, idnsname)


def init():
    """Admin IPA CLI module"""

    @click.group(name='ipa')
    @click.option(
        '--ipa-certs', required=False, envvar='TREADMILL_IPA_CERTS',
        callback=aws_cli.handle_context_opt,
        is_eager=True,
        default='/etc/ipa/ca.crt',
        expose_value=False
    )
    def ipa_grp():
        """Manage treadmill cell."""
        treadmill.logging.set_log_level(logging.INFO)

    @ipa_grp.command()
    @click.option('--add', '-a', required=False, metavar='HOST:PORT',
                  multiple=True,
                  help='Add krb5keytab server endpoints.')
    @click.option('--remove', '-r', required=False, metavar='HOST:PORT',
                  multiple=True,
                  help='Remove krb5keytab server endpoints.')
    @cli.handle_exceptions(_CLI_EXCEPTIONS)
    def krb5keytab(add, remove):
        """Manage krb5keytab configuration."""
        domain = awscontext.GLOBAL.ipa_domain
        ipaclient = awscontext.GLOBAL.ipaclient

        idnsname = '_krb5keytab._tcp.{}'.format(domain)
        for endpoint in sorted(_set_state(ipaclient, idnsname, add, remove)):
            print(endpoint)

    del krb5keytab
    return ipa_grp
