"""Treadmill IPA DNS manager.

   This system process watches Zookeeper's data on app endpoints
   and creates/updates/destroys IPA DNS records when app endpoints change
"""
import logging
import os
import sys

import click

from treadmill import context
from treadmill import utils
from treadmill import zknamespace as z
from treadmill import zkutils
from treadmill_aws import awscontext
from treadmill_aws import dnsmonitor

_LOGGER = logging.getLogger(__name__)


def _do_watch(zkclient, zkfs_dir):
    """Watch proid endpoints for changes.
    """
    dns_monitor = dnsmonitor.DNSMonitor(cell_name=context.GLOBAL.cell,
                                        ipaclient=awscontext.GLOBAL.ipaclient,
                                        zkfs_dir=zkfs_dir)

    @zkclient.ChildrenWatch(zkfs_dir)
    @utils.exit_on_unhandled
    def _endpoint_change(_children):
        _LOGGER.info(
            'Endpoints changed! Updating DNS configuration...'
        )
    dns_monitor.run()


def init():
    """Return top level command handler.
    """

    @click.command()
    @click.option('--no-lock', is_flag=True, default=False,
                  help='Run without lock.')
    @click.option('--proid', required=True,
                  help='System proid to monitor')
    @click.option('--root', default='/tmp/zk2fs',
                  help='ZK2FS root directory')
    def run(no_lock, proid, root):
        """Run Treadmill DNS endpoint engine.
        """
        zkclient = context.GLOBAL.zk.conn

        zkendpointpath = z.join_zookeeper_path(z.ENDPOINTS, proid)
        zkclient.ensure_path(zkendpointpath)
        zk2fs_endpointpath = '{}{}'.format(root, zkendpointpath)

        if not os.path.isabs(zk2fs_endpointpath):
            _LOGGER.error('Invalid path: %s', zk2fs_endpointpath)
            sys.exit(1)

        if no_lock:
            _do_watch(zkclient=zkclient,
                      zkfs_dir=zk2fs_endpointpath)
        else:
            lock = zkutils.make_lock(
                zkclient, z.path.election(__name__)
            )
            _LOGGER.info('Waiting for leader lock.')
            with lock:
                _do_watch(zkclient=zkclient,
                          zkfs_dir=zk2fs_endpointpath)

    return run
