"""Admin Cell CLI module
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill import cli
from treadmill import context
from treadmill.scheduler import masterapi

from treadmill_aws import cli as aws_cli
from treadmill_aws.cli.admin import cell as cell_admin


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.command(name='configure-monitors')
    @click.option('--monitors', type=cli.DICT,
                  help='Key/value pairs for monitor count overrides.')
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
    def configure_monitors(monitors, cors_origin, krb_realm, dry_run):
        """Configure system apps monitors."""
        ctx = cell_admin.CellCtx(cors=cors_origin, krb_realm=krb_realm)
        cell_apps = cell_admin.get_apps(ctx)

        if not monitors:
            monitors = {
                appname: app['monitors'] for appname, app in cell_apps.items()
                if 'monitors' in app
            }

        for appname, count in monitors.items():
            fullname = cell_apps[appname]['fullname']
            cli.echo_green('Configuring monitor %s: %s', fullname, count)
            if not dry_run:
                masterapi.update_appmonitor(
                    context.GLOBAL.zk.conn,
                    fullname,
                    int(count)
                )

    return configure_monitors
