"""Admin module to manage cell capacity
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import random

import click

from treadmill import admin
from treadmill import context
from treadmill import cli
from treadmill.syscall import krb5
from treadmill import sysinfo

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli
from treadmill_aws import hostmanager


_LOGGER = logging.getLogger(__name__)


def _create_servers(count, partition=None):
    """Create new servers in the cell."""

    ipa_client = awscontext.GLOBAL.ipaclient
    ec2_conn = awscontext.GLOBAL.ec2
    sts_conn = awscontext.GLOBAL.sts
    ipa_domain = awscontext.GLOBAL.ipa_domain
    admin_srv = admin.Server(context.GLOBAL.ldap.conn)
    admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
    cell = admin_cell.get(context.GLOBAL.cell)

    data = cell['data']

    image_id = data['image']
    instance_type = data['size']
    subnets = data['subnets']
    secgroup_id = data['secgroup']
    hostgroups = data['hostgroups']
    instance_profile = data['instance_profile']
    disk_size = int(data['disk_size'])
    hostname_template = '{}-{}-{}'.format(
        context.GLOBAL.cell,
        partition.replace('_', '') if partition else 'node',
        '{time}'
    )

    instance_vars = {
        'treadmill_cell': context.GLOBAL.cell,
        'treadmill_ldap': ','.join(context.GLOBAL.ldap.url),
        'treadmill_ldap_suffix': context.GLOBAL.ldap_suffix,
        'treadmill_dns_domain': context.GLOBAL.dns_domain,
        'treadmill_isa': 'node',
        'treadmill_profile': 'aws',
        'treadmill_krb_realm': krb5.get_host_realm(sysinfo.hostname())[0],
    }

    key = None

    subnet_seed = random.randint(0, len(subnets))

    for idx in range(0, count):
        # TODO: need to catch exception that there is no space in the subnet.
        #       if subnet is out of space, we need to retry with next subnet
        #       id (and remove the subnet id from consideration for the rest
        #       of the process).
        subnet_id = subnets[(subnet_seed + idx) % len(subnets)]

        hostnames = hostmanager.create_host(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            image_id=image_id,
            count=1,
            disk=disk_size,
            domain=ipa_domain,
            key=key,
            secgroup_ids=secgroup_id,
            instance_type=instance_type,
            subnet_id=subnet_id,
            role='node',
            instance_vars=instance_vars,
            instance_profile=instance_profile,
            hostgroups=hostgroups,
            hostname=hostname_template,
            ip_address=None,
            eni=None
        )

        # Count is one, but it is more robust to treat it as list.
        for hostname in hostnames:
            print(hostname)
            attrs = {
                'cell': context.GLOBAL.cell,
                'partition': partition
            }
            admin_srv.create(hostname, attrs)


def _delete_servers(count, partition=None):
    """Delete old servers."""
    ipa_client = awscontext.GLOBAL.ipaclient
    ec2_conn = awscontext.GLOBAL.ec2

    admin_srv = admin.Server(context.GLOBAL.ldap.conn)
    servers = admin_srv.list({'cell': context.GLOBAL.cell,
                              'partition': partition})

    hostnames = sorted([s['_id'] for s in servers])
    extra = hostnames[0:count]
    hostmanager.delete_hosts(
        ipa_client=ipa_client,
        ec2_conn=ec2_conn,
        hostnames=extra
    )

    for hostname in extra:
        admin_srv.delete(hostname)


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
    @click.option('--partition', help='Target partition',
                  callback=aws_cli.sanitize_partition_name)
    def scale_cmd(count, partition):
        """Scale nodes to specified count."""
        cell = context.GLOBAL.cell
        admin_srv = admin.Server(context.GLOBAL.ldap.conn)
        servers = admin_srv.list({'cell': cell,
                                  'partition': partition})

        current_count = len(servers)
        if not count or current_count == count:
            print(current_count)
            return

        if count > current_count:
            _create_servers(count - current_count, partition)
        else:
            _delete_servers(current_count - count, partition)

        cli.out(count)

    @nodes_grp.command(name='rotate')
    @click.option('--count', type=int, help='Target node count.')
    @click.option('--partition', help='Target partition', default='_default',
                  callback=aws_cli.sanitize_partition_name)
    def rotate_cmd(count, partition):
        """Rotate nodes, deleting old nodes and starting new."""
        _create_servers(count, partition)
        _delete_servers(count, partition)

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
