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
from treadmill.admin import exc as admin_exceptions

from treadmill_aws import cli as aws_cli

from . import CellCtx
from . import _appgroups


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.command(name='configure-appgroups')
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
    def configure_appgroups(cors_origin, krb_realm):
        """Configure system app groups."""
        ctx = CellCtx(cors=cors_origin, krb_realm=krb_realm)
        appgroups = _appgroups(ctx)

        admin_app_group = admin.AppGroup(context.GLOBAL.ldap.conn)
        for name, data in appgroups.items():
            print(name, data)
            try:
                admin_app_group.create(name, data)
            except admin_exceptions.AlreadyExistsResult:
                admin_app_group.update(name, data)

            existing = admin_app_group.get(name, dirty=True)
            group_cells = set(existing['cells'])
            group_cells.update([context.GLOBAL.cell])
            admin_app_group.update(name, {'cells': list(group_cells)})
            existing = admin_app_group.get(name, dirty=True)
            print(existing)

    return configure_appgroups
