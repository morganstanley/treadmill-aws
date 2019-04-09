"""Admin Cell CLI module
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill import admin
from treadmill import cli
from treadmill import context
from treadmill import yamlwrapper as yaml
from treadmill.admin import exc as admin_exceptions
from treadmill.scheduler import masterapi

from treadmill_aws import cli as aws_cli

from . import CellCtx
from . import _CELL_APPS
from . import _render_app
from . import _ident_groups


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.command(name='configure-apps')
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
    @click.option('--apps', type=cli.LIST, help='List of apps to configure.')
    def configure_apps(cors_origin, krb_realm, apps):
        """Configure cell API."""
        ctx = CellCtx(cors=cors_origin, krb_realm=krb_realm)
        admin_app = admin.Application(context.GLOBAL.ldap.conn)

        # For apps that need write access to LDAP. The context LDAP must have
        # write access because this is what we use to write manifests here.
        write_uri = admin_app.admin.write_uri
        ctx.admin_ldap_url = ','.join(write_uri) if write_uri else None

        if not apps:
            apps = _CELL_APPS

        # Configure apps identity groups
        identity_groups = _ident_groups(ctx)
        for groupname, count in identity_groups.items():
            masterapi.update_identity_group(
                context.GLOBAL.zk.conn,
                groupname,
                count
            )

        # Configure apps
        for appname in apps:
            fullname, app = _render_app(appname, ctx)
            print(fullname)
            print(yaml.dump(app))
            try:
                admin_app.create(fullname, app)
            except admin_exceptions.AlreadyExistsResult:
                admin_app.replace(fullname, app)

    return configure_apps
