"""Admin module to manage cell capacity
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import itertools
import logging

import click

from treadmill import admin
from treadmill import context
from treadmill import cli

import treadmill_aws
from treadmill_aws import autoscale


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.group(name='nodes')
    @click.option('--aws-region', required=False,
                  envvar='AWS_REGION',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    @click.option('--aws-profile', required=False,
                  envvar='AWS_PROFILE',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    @click.option('--ipa-certs', required=False,
                  default='/etc/ipa/ca.crt',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    def nodes_grp():
        """Configure cell nodes."""
        pass

    @nodes_grp.command(name='scale')
    @click.option('--count', type=int, help='Target node count.')
    @click.option('--partition', help='Target partition')
    def scale_cmd(count, partition):
        """Scale nodes to specified count."""
        if partition in ('-', '_default'):
            partition = None

        cell = context.GLOBAL.cell
        admin_srv = admin.Server(context.GLOBAL.ldap.conn)
        by_partition = {}
        for part, srvs in itertools.groupby(admin_srv.list({'cell': cell}),
                                            lambda x: x.get('partition')):
            by_partition[part] = list(srvs)

        current_count = len(by_partition.get(
            partition if partition else '_default',
            []
        ))

        count_by_partition = collections.Counter(
            {p: len(s) for p, s in by_partition.items()}
        )

        if count not in {None, current_count}:
            if count > current_count:
                autoscale.create_n_servers(count - current_count, partition)
            else:
                autoscale.delete_n_servers(current_count - count, partition)

            count_by_partition[partition if partition else '_default'] = count

        for part in sorted(count_by_partition):
            print('{: <32}: {}'.format(part, count_by_partition[part]))

    @nodes_grp.command(name='rotate')
    @click.option('--count', type=int, help='Target node count.', default=1)
    @click.option('--partition', help='Target partition')
    def rotate_cmd(count, partition):
        """Rotate nodes, deleting old nodes and starting new."""
        if partition in ('-', '_default'):
            partition = None

        autoscale.create_n_servers(count, partition)
        autoscale.delete_n_servers(count, partition)

    @nodes_grp.command(name='delete')
    @click.option('--servers', type=cli.LIST)
    def delete_cmd(servers):
        """Delete servers by name."""
        autoscale.delete_servers_by_name(servers)

    return nodes_grp
