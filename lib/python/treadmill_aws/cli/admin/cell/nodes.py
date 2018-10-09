"""Admin module to manage cell capacity
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill import admin
from treadmill import context
from treadmill import cli

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import hostmanager
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
        cell = context.GLOBAL.cell
        admin_srv = admin.Server(context.GLOBAL.ldap.conn)
        servers = admin_srv.list({'cell': cell,
                                  'partition': partition})

        current_count = len(servers)
        if count in {None, current_count}:
            print(current_count)
            return

        if count > current_count:
            autoscale.create_servers(count - current_count, partition)
        else:
            autoscale.delete_servers(current_count - count, partition)

        cli.out(count)

    @nodes_grp.command(name='rotate')
    @click.option('--count', type=int, help='Target node count.')
    @click.option('--partition', help='Target partition')
    def rotate_cmd(count, partition):
        """Rotate nodes, deleting old nodes and starting new."""
        autoscale.create_servers(count, partition)
        autoscale.delete_servers(count, partition)

    @nodes_grp.command(name='delete')
    @click.option('--servers', type=cli.LIST)
    def delete_cmd(servers):
        """Delete servers by name."""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2

        hostmanager.delete_hosts(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            hostnames=servers
        )

        admin_srv = admin.Server(context.GLOBAL.ldap.conn)
        for server in servers:
            admin_srv.delete(server)

    return nodes_grp
