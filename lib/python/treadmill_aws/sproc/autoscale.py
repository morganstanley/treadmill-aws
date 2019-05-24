"""Autoscale Treadmill cell based on scheduler queue."""

import logging
import multiprocessing
import time

import click

from treadmill import context
from treadmill import zkutils

from treadmill_aws import cli as aws_cli
from treadmill_aws import autoscale


_LOGGER = logging.getLogger(__name__)

_DEFAULT_INTERVAL = 60

_DEFAULT_SERVER_APP_RATIO = 0.5

_DEFAULT_IDLE_SERVER_TTL = 5 * 60


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
    @click.option(
        '--idle-server-ttl', required=False, type=int,
        default=_DEFAULT_IDLE_SERVER_TTL,
        help='Default idle server TTL.'
    )
    @click.option(
        '--workers', required=False, type=int,
        help='Number of worker processes to use to create hosts in parallel.'
    )
    def autoscale_cmd(interval, server_app_ratio, idle_server_ttl, workers):
        """Autoscale Treadmill cell based on scheduler queue."""
        pool = None
        if workers:
            pool = multiprocessing.Pool(processes=workers)
            pool.workers = workers

        context.GLOBAL.zk.add_listener(zkutils.exit_on_lost)
        idle_servers_tracker = {}

        while True:
            autoscale.scale(
                server_app_ratio, idle_server_ttl, idle_servers_tracker,
                pool=pool
            )
            time.sleep(interval)

    return autoscale_cmd
