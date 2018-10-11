"""Autoscale Treadmill cell based on scheduler queue."""

import logging
import time

import click

from treadmill_aws import cli as aws_cli
from treadmill_aws import autoscale


_LOGGER = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 60

_DEFAULT_APP_SERVER_RATIO = 0.5


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
        '--timeout', required=False, default=_DEFAULT_TIMEOUT, type=int,
        help='Time interval to evaluate state (seconds).'
    )
    @click.option(
        '--max-count', required=True, type=int,
        help='Max server count.'
    )
    @click.option(
        '--min-count', required=False, type=int, default=0,
        help='Min server count.'
    )
    @click.option(
        '--batch-count', required=True, type=int,
        help='Max batch count for new servers.'
    )
    @click.option(
        '--app-srv-ratio', required=False, type=float,
        default=_DEFAULT_APP_SERVER_RATIO,
        help='Default app/server ratio.'
    )
    def autoscale_cmd(timeout, max_count, min_count, batch_count,
                      app_srv_ratio):
        """Autoscale Treadmill cell based on scheduler queue."""
        while True:
            create_cnt, extra_servers = autoscale.scale(
                max_servers=max_count,
                min_servers=min_count,
                default_app_srv_ratio=app_srv_ratio,
                max_batch=batch_count)
            if create_cnt > 0:
                autoscale.create_n_servers(create_cnt, partition=None)

            if extra_servers:
                autoscale.delete_servers_by_name(extra_servers)

            time.sleep(timeout)

    return autoscale_cmd
