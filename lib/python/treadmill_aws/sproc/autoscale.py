"""Autoscale Treadmill cell based on scheduler queue."""

import logging
import time

import click

from treadmill_aws import cli as aws_cli
from treadmill_aws import autoscale


_LOGGER = logging.getLogger(__name__)

_DEFAULT_INTERVAL = 60

_DEFAULT_SERVER_APP_RATIO = 0.5


def init():
    """Autoscale Treadmill cell capacity."""

    @click.command(name='autoscale')
    @click.option(
        '--ipa-certs', required=False, envvar='TREADMILL_IPA_CERTS',
        callback=aws_cli.handle_context_opt,
        is_eager=True,
        default='/etc/ipa/ca.crt',
        expose_value=False
    )
    @click.option(
        '--interval', required=False, default=_DEFAULT_INTERVAL, type=int,
        help='Time interval to evaluate state (seconds).'
    )
    @click.option(
        '--server-app-ratio', required=False, type=float,
        default=_DEFAULT_SERVER_APP_RATIO,
        help='Default server/app ratio.'
    )
    def autoscale_cmd(interval, server_app_ratio):
        """Autoscale Treadmill cell based on scheduler queue."""
        while True:
            autoscale.scale(server_app_ratio)
            time.sleep(interval)

    return autoscale_cmd
