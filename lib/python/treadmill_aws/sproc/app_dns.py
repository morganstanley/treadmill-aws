"""Syncronize dns app groups with IPA dns."""

import logging
import os
import time

import click

from treadmill import cli
from treadmill import context
from treadmill import zknamespace as z
from treadmill import zkutils
from treadmill.zksync import utils as zksync_utils

from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli
from treadmill_aws import dns_sync

_LOGGER = logging.getLogger(__name__)


def init():
    """Treadmill App DNS"""

    @click.command(name='app-dns')
    @click.option(
        '--ipa-certs', required=False, envvar='TREADMILL_IPA_CERTS',
        callback=aws_cli.handle_context_opt,
        is_eager=True,
        default='/etc/ipa/ca.crt',
        expose_value=False
    )
    @click.option(
        '--fs-root',
        help='Root file system directory to zk2fs',
        required=True
    )
    @click.option('--scopes', help='List of cell DNS scopes.', type=cli.DICT)
    @click.option(
        '--no-lock',
        is_flag=True,
        default=False,
        help='Run without lock.'
    )
    def appdns(fs_root, scopes, no_lock):
        """Start Treadmill App DNS"""
        cell = context.GLOBAL.cell
        if not scopes:
            scopes = {}

        # keep sleeping until zksync ready
        modified = zksync_utils.wait_for_ready(fs_root)

        sync = dns_sync.DnsSync(
            awscontext.GLOBAL.ipaclient,
            cell,
            context.GLOBAL.dns_domain,
            fs_root,
            scopes
        )

        def _run():
            """Run sync process."""
            modified_at = 0
            while True:
                new_modified = os.stat(modified).st_mtime
                if new_modified > modified_at:
                    sync.sync()
                    modified_at = new_modified

                time.sleep(5)

        if not no_lock:
            lock = zkutils.make_lock(context.GLOBAL.zk.conn,
                                     z.path.election(__name__))

            _LOGGER.info('Waiting for leader lock.')
            with lock:
                _run()
        else:
            _LOGGER.info('Running without lock.')
            _run()

    return appdns
