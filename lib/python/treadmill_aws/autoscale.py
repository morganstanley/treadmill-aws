"""Autoscale cell capacity."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import functools
import logging
import math
import re
import time

from ldap3.core import exceptions as ldap_exceptions
from botocore import exceptions as botoexc

from treadmill import context
from treadmill import sysinfo
from treadmill import restclient
from treadmill.syscall import krb5

from treadmill_aws import aws
from treadmill_aws import awscontext
from treadmill_aws import hostmanager
from treadmill_aws import ec2client


_LOGGER = logging.getLogger(__name__)

_SCHEDULER_APPS_URL = '/scheduler/apps'
_SCHEDULER_SERVERS_URL = '/scheduler/servers'

# Max time for server to register state after being created.
_SERVER_START_INTERVAL = 5 * 60


class ExpiredTokenError(Exception):
    """Error indicating that AWS token expired."""
    pass


def check_expired_token(func):
    """Decorator to simplify handling of expired token error."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except botoexc.ClientError as err:
            if err.response['Error']['Code'] == 'ExpiredToken':
                raise ExpiredTokenError
            raise
    return wrapper


@check_expired_token
def _create_hosts(hostnames, subnets, cell, partition, **host_params):
    hosts_created = []
    for hostname in hostnames:
        _LOGGER.info('Creating host %s', hostname)
        hostmanager.create_host(
            ipa_client=awscontext.GLOBAL.ipaclient,
            ec2_conn=awscontext.GLOBAL.ec2,
            hostname=hostname,
            subnets=subnets,
            **host_params
        )
        admin_srv = context.GLOBAL.admin.server()
        admin_srv.create(
            hostname,
            {'cell': cell, 'partition': partition}
        )
        hosts_created.append(hostname)
    return hosts_created


def _create_hosts_no_exc(hostnames, subnets, cell, partition, **host_params):
    try:
        hosts_created = _create_hosts(
            hostnames, subnets, cell, partition, **host_params
        )
        return hosts_created, None
    except ExpiredTokenError as err:
        _LOGGER.exception('Error creating hosts: %r', hostnames)
        return None, err
    except Exception as err:  # pylint: disable=broad-except
        _LOGGER.exception('Error creating hosts: %r', hostnames)
        # Make sure error can be pickled (e.g. botocore exceptions can't).
        return None, Exception(str(err))


def _generate_hostnames(domain, cell, partition, count):
    hostname_template = '{}-{}-{}'.format(cell, partition, '{time}')

    # Sanitize DNS name.
    hostname_template = re.sub(r'[^a-zA-Z0-9-{}]', '', hostname_template)

    # Generate hostnames in a loop, append seq. no. in case time is not unique.
    return [
        hostmanager.generate_hostname(
            domain,
            '{}{}'.format(hostname_template, i)
        )
        for i in range(count)
    ]


def _split_list(lst, num_parts):
    parts = [lst[i::num_parts] for i in range(num_parts)]
    return [part for part in parts if part]


@aws.profile
@check_expired_token
def create_n_servers(count, partition=None, pool=None):
    """Create new servers in the cell."""

    partition = partition or '_default'  # FIXME: Import name from treadmill.

    ec2_conn = awscontext.GLOBAL.ec2
    sts_conn = awscontext.GLOBAL.sts
    ipa_domain = awscontext.GLOBAL.ipa_domain

    admin_srv = context.GLOBAL.admin.server()
    admin_cell = context.GLOBAL.admin.cell()
    cell = context.GLOBAL.cell
    cell_data = admin_cell.get(cell)['data']

    admin_part = context.GLOBAL.admin.partition()
    try:
        _ldap_data = admin_part.get([partition, cell], dirty=True)
        partition_data = _ldap_data.get('data', {})
    except ldap_exceptions.LDAPNoSuchObjectResult:
        partition_data = {}

    image_id = partition_data.get('image', cell_data['image'])
    if not image_id.startswith('ami-'):
        account = sts_conn.get_caller_identity().get('Account')
        image_id = ec2client.get_image(
            ec2_conn, owners=[account], name=image_id
        )['ImageId']

    instance_type = partition_data.get('size', cell_data['size'])
    subnets = partition_data.get('subnets', cell_data['subnets'])
    secgroup_id = partition_data.get('secgroup', cell_data['secgroup'])
    hostgroups = partition_data.get('hostgroups', cell_data['hostgroups'])
    instance_profile = partition_data.get('instance_profile',
                                          cell_data['instance_profile'])
    disk_size = int(partition_data.get('disk_size', cell_data['disk_size']))
    nshostlocation = cell_data['aws_account']

    instance_vars = {
        'treadmill_cell': cell,
        'treadmill_ldap': ','.join(context.GLOBAL.ldap.url),
        'treadmill_ldap_suffix': context.GLOBAL.ldap_suffix,
        'treadmill_dns_domain': context.GLOBAL.dns_domain,
        'treadmill_isa': 'node',
        'treadmill_profile': 'aws',
        'treadmill_krb_realm': krb5.get_host_realm(sysinfo.hostname())[0],
    }

    tags = [
        {'Key': 'Cell', 'Value': cell},
        {'Key': 'Partition', 'Value': partition},
    ]

    hostnames = _generate_hostnames(ipa_domain, cell, partition, count)
    host_params = dict(
        image_id=image_id,
        count=1,
        disk=disk_size,
        domain=ipa_domain,
        key=None,
        secgroup_ids=secgroup_id,
        instance_type=instance_type,
        role='node',
        instance_vars=instance_vars,
        instance_profile=instance_profile,
        hostgroups=hostgroups,
        ip_address=None,
        eni=None,
        tags=tags,
        nshostlocation=nshostlocation
    )
    if pool:
        func = functools.partial(
            _create_hosts_no_exc,
            subnets=subnets,
            cell=cell,
            partition=partition,
            **host_params
        )
        hosts_created = []
        for res, err in pool.map(func, _split_list(hostnames, pool.workers)):
            if err:
                raise err
            hosts_created.extend(res)
        return hosts_created
    else:
        return _create_hosts(
            hostnames, subnets, cell, partition, **host_params
        )


@check_expired_token
def delete_n_servers(count, partition=None):
    """Delete old servers."""
    ipa_client = awscontext.GLOBAL.ipaclient
    ec2_conn = awscontext.GLOBAL.ec2

    admin_srv = context.GLOBAL.admin.server()
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


@check_expired_token
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

    admin_srv = context.GLOBAL.admin.server()
    for server in servers:
        admin_srv.delete(server)


def _query_stateapi():
    state_api = context.GLOBAL.state_api()
    apps_state = restclient.get(state_api, _SCHEDULER_APPS_URL).json()
    servers_state = restclient.get(state_api, _SCHEDULER_SERVERS_URL).json()
    return apps_state, servers_state


def _get_state():
    apps_state, servers_state = _query_stateapi()

    apps_by_partition = collections.defaultdict(list)
    servers_by_partition = collections.defaultdict(list)

    num_apps_by_server = collections.Counter()
    state_by_server = {}

    # Process apps state.
    col_idx = {name: idx for idx, name in enumerate(apps_state['columns'])}
    for row in apps_state['data']:
        app = {name: row[idx] for name, idx in col_idx.items()}

        if app['server']:
            num_apps_by_server[app['server']] += 1

        apps_by_partition[app['partition']].append({
            'instance': app['instance'],
            'server': app['server'],
        })

    # Process servers state.
    col_idx = {name: idx for idx, name in enumerate(servers_state['columns'])}
    for row in servers_state['data']:
        server = {name: row[idx] for name, idx in col_idx.items()}

        # If capacity is empty, server didn't report it's state, handled below.
        if server['cpu'] and server['mem'] and server['disk']:
            state_by_server[server['name']] = server['state']

    servers = context.GLOBAL.admin.server().list(
        {'cell': context.GLOBAL.cell},
        get_operational_attrs=True
    )
    for server in servers:
        server_name = server['_id']
        server_create_timestamp = server['_create_timestamp']

        # If server didn't report it's state, it's either new/starting or down.
        # Consider server to be new if it's just been created, down otherwise.
        # Autoscaler will treat new server like up/idle, but won't delete it.
        server_state = state_by_server.get(server_name)
        if not server_state:
            if time.time() - server_create_timestamp <= _SERVER_START_INTERVAL:
                server_state = 'new'
            else:
                server_state = 'down'

        servers_by_partition[server['partition']].append({
            'name': server_name,
            'state': server_state,
            'create_timestamp': server_create_timestamp,
            'num_apps': num_apps_by_server[server_name],
        })

    return apps_by_partition, servers_by_partition


def _count(apps, servers):
    pending_apps = len([app for app in apps if not app['server']])
    running_apps = 0
    busy_servers = 0
    idle_servers = 0

    for server in servers:
        if server['state'] in ('new', 'up'):
            if server['num_apps']:
                busy_servers += 1
                running_apps += server['num_apps']
            else:
                idle_servers += 1

    return pending_apps, running_apps, busy_servers, idle_servers


def _select_extra_servers(servers, state, max_extra_servers=None):
    extra_servers = []
    for server in servers:
        if max_extra_servers is not None:
            if len(extra_servers) == max_extra_servers:
                return extra_servers

        if server['num_apps']:
            continue

        if server['state'] not in state:
            continue

        extra_servers.append(server['name'])
    return extra_servers


def _scale_partition(server_app_ratio, autoscale_conf, apps, servers):
    min_servers = int(autoscale_conf['min_servers'])
    max_servers = int(autoscale_conf['max_servers'])
    server_app_ratio = float(autoscale_conf.get('server_app_ratio',
                                                server_app_ratio))

    _LOGGER.debug('Apps: %r', apps)
    _LOGGER.debug('Servers: %r', servers)

    # Scaling rules:
    #
    # - If there are pending apps, add servers unless we have enough idle ones.
    #   Servers needed = ceil(pending apps * ratio) - idle_servers.
    #   Notice invariant: ratio = busy_servers / running_apps <= 1.
    # - If there are no pending apps, shutdown idle servers (skip new servers).
    # - If there are pending apps and we have enough idle servers, shutdown
    #   (idle servers - pending apps) servers (skip new servers).
    # - Shutdown down and frozen servers that have no apps placed on them.
    # - Server count can't exceed max_servers or be less than min_servers.
    #   Only new and up servers count towards min_serves, down or frozen don't.

    pending_apps, running_apps, busy_servers, idle_servers = _count(
        apps, servers
    )

    new_servers = 0
    max_new_servers = max(0, max_servers - len(servers))

    if running_apps > 0:
        ratio = float(busy_servers) / float(running_apps)
    else:
        ratio = server_app_ratio
    _LOGGER.info('Ratio: %s', ratio)

    if pending_apps > 0:
        servers_needed = max(
            0,
            math.ceil(float(pending_apps) * ratio) - idle_servers
        )
        new_servers = min(servers_needed, max_new_servers)
        _LOGGER.info('Pending apps: %d, idle servers: %d, needed: %d, new: %d',
                     pending_apps, idle_servers, servers_needed, new_servers)

    active_servers = busy_servers + idle_servers

    if active_servers + new_servers < min_servers:
        servers_needed = min_servers - active_servers - new_servers
        add_servers = min(servers_needed, max_new_servers - new_servers)
        _LOGGER.info('Min servers: %d, needed: %d, add: %d',
                     min_servers, servers_needed, add_servers)
        new_servers += add_servers

    _LOGGER.info('Final new server count: %s', new_servers)

    extra_servers = []
    if not new_servers:
        max_extra_servers = min(
            max(0, idle_servers - pending_apps),
            max(0, active_servers - min_servers)
        )
        extra_servers = _select_extra_servers(
            servers, ('up'), max_extra_servers
        )
    extra_servers += _select_extra_servers(servers, ('down', 'frozen'))
    _LOGGER.info('Empty servers to delete: %r', extra_servers)

    return new_servers, extra_servers


def scale(server_app_ratio, pool=None):
    """Autoscale cell capacity."""
    _LOGGER.info('Getting cell state')
    apps_by_partition, servers_by_partition = _get_state()

    _LOGGER.info('Getting cell partitions')
    cell = context.GLOBAL.admin.cell().get(context.GLOBAL.cell)

    for partition in cell['partitions']:
        partition_name = partition['_id']
        try:
            autoscale_conf = partition['data']['autoscale']
        except KeyError:
            autoscale_conf = None

        if autoscale_conf:
            try:
                _LOGGER.info('Scaling partition %s: %r',
                             partition_name, autoscale_conf)
                new_servers, extra_servers = _scale_partition(
                    server_app_ratio, autoscale_conf,
                    apps_by_partition.get(partition_name, []),
                    servers_by_partition.get(partition_name, [])
                )
                if new_servers > 0:
                    create_n_servers(new_servers, partition_name, pool=pool)
                if extra_servers:
                    delete_servers_by_name(extra_servers)
            except ExpiredTokenError:
                raise
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception('Error while scaling partition %s: %r',
                                  partition_name, err)
