"""Autoscale cell capacity."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import random

from treadmill import admin
from treadmill import context
from treadmill.syscall import krb5
from treadmill import sysinfo

from treadmill_aws import awscontext
from treadmill_aws import hostmanager
from treadmill_aws import ec2client


_LOGGER = logging.getLogger(__name__)


def create_servers(count, partition=None):
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
    if not image_id.startswith('ami-'):
        account = sts_conn.get_caller_identity().get('Account')
        image_id = ec2client.get_image(
            ec2_conn, owners=[account], name=image_id
        )['ImageId']

    instance_type = data['size']
    subnets = data['subnets']
    secgroup_id = data['secgroup']
    hostgroups = data['hostgroups']
    instance_profile = data['instance_profile']
    disk_size = int(data['disk_size'])
    hostname_template = '{}-{}-{}'.format(
        context.GLOBAL.cell,
        partition if partition else 'node',
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


def delete_servers(count, partition=None):
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
