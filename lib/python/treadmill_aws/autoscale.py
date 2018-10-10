"""Autoscale cell capacity."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from collections import namedtuple
import logging
import math
import random

from treadmill import admin
from treadmill import context
from treadmill import sysinfo
from treadmill import restclient
from treadmill.syscall import krb5

from treadmill_aws import awscontext
from treadmill_aws import hostmanager
from treadmill_aws import ec2client


_LOGGER = logging.getLogger(__name__)

_STATE_URL = '/state/'

_STATE = namedtuple('state', 'running pending busy_srv_cnt idle_servers')


def create_n_servers(count, partition=None):
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


def delete_n_servers(count, partition=None):
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


def delete_servers_by_name(servers):
    """Delete servers by name."""
    ipa_client = awscontext.GLOBAL.ipaclient
    ec2_conn = awscontext.GLOBAL.ec2

    _LOGGER.info('Deleting servers: %r', servers)

    hostmanager.delete_hosts(
        ipa_client=ipa_client,
        ec2_conn=ec2_conn,
        hostnames=servers
    )

    admin_srv = admin.Server(context.GLOBAL.ldap.conn)
    for server in servers:
        admin_srv.delete(server)


def scale(min_servers, max_servers, default_app_srv_ratio, max_batch):
    """Process state.
    """

    state = _state()
    running = state.running
    pending = state.pending
    busy_srv_cnt = state.busy_srv_cnt
    idle_servers = state.idle_servers
    running, pending, busy_srv_cnt, idle_servers = _state()

    # Rules of scale:
    #
    # - If there are no pending apps, shutdown idle server.
    # - If there are pending apps and idle server, shutdown (idle - pending)
    #   servers.
    # - Skip servers that are newer than 15 min.
    # - Target server count = (busy_servers/running_apps) * total_apps.
    #   Notice invariant: busy_server / running_apps <= 1
    # - Server count can't exceed max_servers or be less than min_servers.
    # - Servers can't grow more than max_batch at single iteration.

    if running > 0:
        ratio = float(busy_srv_cnt) / float(running)
    else:
        ratio = default_app_srv_ratio

    if pending > 0:
        # if there are enough idle servers, nothing to create for now.
        servers_needed = max(
            0,
            math.ceil(float(pending) * ratio) - len(idle_servers)
        )
    else:
        servers_needed = 0

    new_server_cnt = min(max_batch, servers_needed)
    _LOGGER.info('Projected servers to create: %s', new_server_cnt)

    # check if total projected server count does not exceed max_servers.
    exceed_limit = max(
        0,
        busy_srv_cnt + len(idle_servers) + new_server_cnt - max_servers
    )

    _LOGGER.info('Target servers exceed limit by: %s', exceed_limit)

    final_new_server_cnt = max(
        0,
        new_server_cnt - exceed_limit
    )

    _LOGGER.info('Final new server count: %s', final_new_server_cnt)

    extra = []
    if final_new_server_cnt == 0:
        extra = _select_idle_servers(idle_servers, pending)

        # Ensure that there will be at least min_servers left.
        idle_srv_cnt = len(idle_servers)
        extra_cnt = len(extra)

        if busy_srv_cnt + idle_srv_cnt - extra_cnt < min_servers:
            extra = extra[
                min_servers - (busy_srv_cnt + idle_srv_cnt - extra_cnt):
            ]

    return final_new_server_cnt, extra


def _state():
    """Return tuple that represents current state:

    (running_apps_count,
     pending_apps_count,
     busy_server_count,
     idle_servers)
    """
    cellapis = context.GLOBAL.state_api()
    response = restclient.get(cellapis, _STATE_URL)

    apps = response.json()

    admin_srv = admin.Server(context.GLOBAL.ldap.conn)

    running = 0
    pending = 0
    busy_servers = set()
    for app in apps:
        if app['host']:
            running += 1
            busy_servers.add(app['host'])
        else:
            pending += 1

    _LOGGER.info('Apps: running: %s, pending: %s', running, pending)

    servers = admin_srv.list({'cell': context.GLOBAL.cell})
    all_servers = {s['_id'] for s in servers}

    idle_servers = all_servers - busy_servers
    _LOGGER.info(
        'Servers: busy: %s, idle: %s',
        len(busy_servers),
        len(idle_servers)
    )

    return _STATE(
        running=running,
        pending=pending,
        busy_srv_cnt=len(busy_servers),
        idle_servers=list(idle_servers)
    )


def _select_idle_servers(idle_servers, pending):
    """Remove idle servers.
    """
    _LOGGER.info(
        'Idle servers cleanup - idle: %s, pending: %s',
        idle_servers,
        pending
    )

    extra = []
    can_remove = len(idle_servers) - pending
    if can_remove > 0:
        _LOGGER.info('Can delete idle servers: %s', can_remove)
        extra = idle_servers[0:can_remove]

    return extra
