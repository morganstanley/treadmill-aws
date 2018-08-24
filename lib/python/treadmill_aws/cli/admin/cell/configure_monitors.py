"""Admin Cell CLI module
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click
import six

from treadmill import cli
from treadmill import context
from treadmill.scheduler import masterapi

from treadmill_aws import cli as aws_cli

from . import CellCtx
from . import _monitors


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
    def configure_monitors(monitors, cors_origin, krb_realm):
        """Configure system apps monitors."""
        ctx = CellCtx(cors=cors_origin, krb_realm=krb_realm)

        if not monitors:
            monitors = _monitors(ctx)

        for name, count in six.iteritems(monitors):
            print(name, count)
            masterapi.update_appmonitor(
                context.GLOBAL.zk.conn,
                name,
                int(count)
            )

    return configure_monitors
