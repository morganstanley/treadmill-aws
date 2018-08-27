"""Admin Cell CLI module
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time

import click
import six

from treadmill import cli
from treadmill import yamlwrapper as yaml
from treadmill.api import instance

from treadmill_aws import cli as aws_cli

from . import CellCtx
from . import _monitors
from . import _render_app


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
    def restart_apps(wait, apps, cors_origin, krb_realm):
        """Restart cell API."""
        ctx = CellCtx(cors=cors_origin, krb_realm=krb_realm)

        instance_api = instance.API(plugins=['aws-proid-env'])
        monitors = _monitors(ctx)
        for name, count in six.iteritems(monitors):
            _, appname, _ = name.split('.')
            if apps and appname not in apps:
                continue

            _, app = _render_app(appname, ctx)
            print(name)
            print(yaml.dump(app))
            for idx in range(0, count):
                instance_ids = instance_api.create(name, app, 1)
                for inst_id in instance_ids:
                    print(inst_id)
                if idx <= count - 1 and wait:
                    time.sleep(wait)

    return restart_apps
