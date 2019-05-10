"""Admin Cell CLI module
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time

import click

from treadmill import cli
from treadmill import yamlwrapper as yaml
from treadmill.api import instance

from treadmill_aws import cli as aws_cli
from treadmill_aws.cli.admin import cell as cell_admin


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.command(name='restart-apps')
    @click.option('--apps', type=cli.LIST,
                  help='List of apps to restart.')
    @click.option('--wait', type=int, help='Interval to wait before re-start.',
                  default=20)
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
    def restart_apps(apps, wait, cors_origin, krb_realm, dry_run):
        """Restart system apps."""
        ctx = cell_admin.CellCtx(cors=cors_origin, krb_realm=krb_realm)
        cell_apps = cell_admin.get_apps(ctx)

        if not apps:
            apps = list(cell_apps)

        instance_api = instance.API(plugins=['aws-proid-env'])

        for appname in apps:
            fullname = cell_apps[appname]['fullname']
            app = cell_admin.render_template(appname, ctx)

            count = cell_apps[appname].get('monitors')
            if count is None:
                continue

            cli.echo_green('Restarting app %s:', fullname)
            cli.out(yaml.dump(app, explicit_start=True))

            if dry_run:
                continue

            for idx in range(0, count):
                instance_ids = instance_api.create(fullname, app, 1)
                for inst_id in instance_ids:
                    cli.echo_green(inst_id)
                if idx <= count - 1 and wait:
                    time.sleep(wait)

    return restart_apps
