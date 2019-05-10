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
from treadmill_aws.cli.admin import cell as cell_admin


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.command(name='configure-apps')
    @click.option('--apps', type=cli.LIST, help='List of apps to configure.')
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
    @click.option('--dry-run', help='Dry run.', is_flag=True, default=False)
    def configure_apps(apps, cors_origin, krb_realm, dry_run):
        """Configure system apps."""
        ctx = cell_admin.CellCtx(cors=cors_origin, krb_realm=krb_realm)
        cell_apps = cell_admin.get_apps(ctx)

        if not apps:
            apps = list(cell_apps)

        admin_app = admin.Application(context.GLOBAL.ldap.conn)

        # For apps that need write access to LDAP. The context LDAP must have
        # write access because this is what we use to write manifests here.
        write_uri = context.GLOBAL.ldap.write_url
        ctx.admin_ldap_url = ','.join(write_uri) if write_uri else None

        # Configure apps identity groups
        identity_groups = cell_admin.get_identity_groups(ctx)
        for groupname, count in identity_groups.items():
            cli.echo_green(
                'Configuring identity group %s: %d', groupname, count
            )
            if not dry_run:
                masterapi.update_identity_group(
                    context.GLOBAL.zk.conn,
                    groupname,
                    count
                )

        # Configure apps
        for appname in apps:
            fullname = cell_apps[appname]['fullname']
            app = cell_admin.render_template(appname, ctx)

            cli.echo_green('Configuring app %s:', fullname)
            cli.out(yaml.dump(app, explicit_start=True))

            if not dry_run:
                try:
                    admin_app.create(fullname, app)
                except admin_exceptions.AlreadyExistsResult:
                    admin_app.replace(fullname, app)

    return configure_apps
