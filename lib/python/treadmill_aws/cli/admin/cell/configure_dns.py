"""Admin Cell CLI module
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill import admin
from treadmill import context

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import ipaclient
from treadmill_aws import cli as aws_cli

from . import CellCtx


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.command(name='configure-dns')
    @click.option('--cors-origin', help='CORS origin for API.')
    @click.option(
        '--krb-realm', help='Kerberos realm',
        envvar='TREADMILL_KRB_REALM',
        required=False
    )
    @click.option(
        '--ipa-certs', required=False, envvar='TREADMILL_IPA_CERTS',
        callback=aws_cli.handle_context_opt,
        is_eager=True,
        default='/etc/ipa/ca.crt',
        expose_value=False
    )
    @click.option(
        '--ipa-domain', required=False,
        envvar='IPA_DOMAIN',
        callback=treadmill_aws.cli.handle_context_opt,
        is_eager=True,
        expose_value=False
    )
    def configure_dns(cors_origin, krb_realm):
        """Configure DNS cell records."""

        ctx = CellCtx(cors=cors_origin, krb_realm=krb_realm)
        cellname = context.GLOBAL.cell

        ipa_client = awscontext.GLOBAL.ipaclient
        idnsname = 'zk.{}'.format(cellname)

        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(cellname)

        masters = ','.join(['{}:{}'.format(m['hostname'], m['zk-client-port'])
                            for m in cell['masters']])
        scheme = cell.get('zk-auth-scheme')
        if not scheme:
            scheme = 'zookeeper'

        zkurl = '{scheme}://{username}@{hostports}/treadmill/{cell}'.format(
            scheme=scheme,
            username=ctx.proid,
            hostports=masters,
            cell=cellname
        )

        found = False
        try:
            current_rec = ipa_client.get_dns_record(idnsname)
        except ipaclient.NotFoundError:
            current_rec = None

        if current_rec:
            for record in current_rec['txtrecord']:
                if record != zkurl:
                    _LOGGER.info(
                        'Deleting stale TXT record: %s %s', idnsname, record
                    )
                    ipa_client.delete_txt_record(idnsname, record)
                else:
                    found = True

        if found:
            _LOGGER.info('Zookeeper TXT records up to date: %s : %s',
                         idnsname, zkurl)
            return

        ipa_client.add_txt_record(idnsname, zkurl)

    return configure_dns
