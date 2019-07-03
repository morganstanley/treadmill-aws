"""Autoscale cell capacity."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import collections
import functools
import logging
import math
import random
import re
import time

from botocore import exceptions as botoexc
import kazoo

from treadmill import context
from treadmill import presence
from treadmill import sysinfo
from treadmill import restclient
from treadmill import zknamespace as z
from treadmill.admin import exc as admin_exceptions
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

_CREATE_HOST_MAX_TRIES = 3


class InstanceFeasibilityTracker:
    """Tracks instance creation failures."""

    def __init__(self):
        self._excluded_subnets = set()
        self._excluded_instances = set()

    def feasible(self, instance_type, spot, subnet):
        """Checks if it is feasible to try creating an instance."""
        if subnet in self._excluded_subnets:
            return False

        if (instance_type, spot, subnet) in self._excluded_instances:
            return False

        return True

    def exclude_instance(self, instance_type, spot, subnet):
        """Exclude instance type + lifecycle within given subnet."""
        self._excluded_instances.add(
            (instance_type, spot, subnet)
        )

    def exclude_subnet(self, subnet):
        """Exclude subnet."""
        self._excluded_subnets.add(subnet)


class ExpiredCredentialsError(Exception):
    """Error indicating that AWS credentials expired."""
    pass


def _check_expired_credentials(func):
    """Decorator to simplify handling of expired credentials errors."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Wrapper function."""
        try:
            return func(*args, **kwargs)
        except botoexc.ClientError as err:
            err_code = err.response['Error']['Code']
            if err_code in ('ExpiredToken', 'RequestExpired'):
                raise ExpiredCredentialsError(err_code)
            raise
    return wrapper


def _no_exc(func):
    """Decorator to make function return res, err instead of raising exception.

    Wraps functions for Pool.map (multiprocessing), ensures err can be pickled.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        """Wrapper function."""
        try:
            res = func(*args, **kwargs)
            return res, None
        except ExpiredCredentialsError as err:
            _LOGGER.exception('%s error: %r, %r', func.__name__, args, kwargs)
            return None, err
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception('%s error: %r, %r', func.__name__, args, kwargs)
            # Make sure error can be pickled (e.g. botocore exceptions can't).
            return None, Exception(str(err))
    return wrapper


def _create_host(ipa_client, ec2_conn, hostname, instance_type, spot, subnets,
                 otp, tracker, **host_params):
    for subnet in subnets:
        if not tracker.feasible(instance_type, spot, subnet):
            continue

        _LOGGER.info('Creating host %s, type: %s, spot: %s, subnet: %s',
                     hostname, instance_type, spot, subnet)

        for i in range(_CREATE_HOST_MAX_TRIES):
            try:
                hostmanager.create_host(
                    ipa_client=ipa_client,
                    ec2_conn=ec2_conn,
                    hostname=hostname,
                    subnet=subnet,
                    instance_type=instance_type,
                    spot=spot,
                    otp=otp,
                    **host_params
                )
                return {
                    'hostname': hostname,
                    'type': instance_type,
                    'lifecycle': 'spot' if spot else 'on-demand',
                    'subnet': subnet,
                }
            except botoexc.ClientError as err:
                err_code = err.response['Error']['Code']
                if err_code in (
                        'SpotMaxPriceTooLow',
                        'InsufficientInstanceCapacity'
                ):
                    _LOGGER.info('Instance not feasible, trying next: %r', err)
                    tracker.exclude_instance(instance_type, spot, subnet)
                    break
                elif err_code == 'InsufficientFreeAddressesInSubnet':
                    _LOGGER.info('Subnet exhausted, trying next: %r', err)
                    tracker.exclude_subnet(subnet)
                    break
                elif err_code == 'InternalError':
                    if i == _CREATE_HOST_MAX_TRIES - 1:
                        raise
                    _LOGGER.error('Internal error, retrying: %r', err)
                else:
                    raise
    return None


@_check_expired_credentials
def _create_hosts(hostnames, instance_types, subnets, cell, partition,
                  **host_params):
    admin_srv = context.GLOBAL.admin.server()
    ipa_client = awscontext.GLOBAL.ipaclient
    ec2_conn = awscontext.GLOBAL.ec2
    subnets = subnets.copy()
    hosts_created = []

    tracker = InstanceFeasibilityTracker()

    for hostname, try_spot, try_on_demand in hostnames:
        _LOGGER.info('Creating host %s, try spot: %s, try on-demand: %s',
                     hostname, try_spot, try_on_demand)

        otp = hostmanager.create_otp(
            ipa_client, hostname, host_params['hostgroups'],
            nshostlocation=host_params['nshostlocation']
        )

        random.shuffle(subnets)

        for instance_type, spot in instance_types:
            if spot and not try_spot:
                continue

            if not spot and not try_on_demand:
                continue

            host = _create_host(
                ipa_client, ec2_conn, hostname, instance_type, spot, subnets,
                otp, tracker, **host_params
            )
            if host:
                break
        else:
            raise Exception('Failed to create host %s' % hostname)

        admin_srv.create(
            host['hostname'],
            {
                'cell': cell,
                'partition': partition,
                'data': {
                    'type': host['type'],
                    'lifecycle': host['lifecycle'],
                },
            }
        )
        hosts_created.append(host)
    return hosts_created


@_check_expired_credentials
def _delete_hosts(hostnames):
    ec2_conn = awscontext.GLOBAL.ec2
    ipa_client = awscontext.GLOBAL.ipaclient
    admin_srv = context.GLOBAL.admin.server()

    hostmanager.delete_hosts(
        ipa_client=ipa_client,
        ec2_conn=ec2_conn,
        hostnames=hostnames
    )

    for hostname in hostnames:
        admin_srv.delete(hostname)


@_no_exc
def _create_hosts_no_exc(hostnames, instance_types, subnets, cell, partition,
                         **host_params):
    return _create_hosts(hostnames, instance_types, subnets, cell, partition,
                         **host_params)


@_no_exc
def _delete_hosts_no_exc(hostnames):
    return _delete_hosts(hostnames)


def _generate_hostnames(domain, cell, partition, count,
                        min_on_demand=None, max_on_demand=None):
    hostname_template = '{}-{}-{}'.format(cell, partition, '{time}')

    # Sanitize DNS name.
    hostname_template = re.sub(r'[^a-zA-Z0-9-{}]', '', hostname_template)

    # All hosts are on-demand by default.
    if min_on_demand is None and max_on_demand is None:
        min_on_demand = max_on_demand = count

    hostnames = []
    # Generate hostnames in a loop, append seq. no. in case time is not unique.
    # For each generated hostname, figure instance lifecycle (on-demand/spot):
    # - First min_on_demand are on-demand.
    # - Next max_on_demand - min_on_demand are spot, can fallback to on-demand.
    # - Remaining ones are spot.
    for i in range(count):
        hostname = hostmanager.generate_hostname(
            domain,
            '{}{}'.format(hostname_template, i)
        )
        if min_on_demand:
            try_spot = False
            try_on_demand = True
            min_on_demand -= 1
            if max_on_demand:
                max_on_demand -= 1
        elif max_on_demand:
            try_spot = try_on_demand = True
            max_on_demand -= 1
        else:
            try_spot = True
            try_on_demand = False
        hostnames.append((hostname, try_spot, try_on_demand))
    return hostnames


def _split_list(lst, num_parts):
    parts = [lst[i::num_parts] for i in range(num_parts)]
    return [part for part in parts if part]


def _instance_types(instance_types, spot_instance_types):
    res = [
        (instance_type, True) for instance_type in spot_instance_types
    ]
    res.extend([
        (instance_type, False) for instance_type in instance_types
    ])
    return res


@aws.profile
@_check_expired_credentials
def create_n_servers(count, partition=None,
                     min_on_demand=None, max_on_demand=None, pool=None):
    """Create new servers in the cell."""

    partition = partition or '_default'  # FIXME: Import name from treadmill.

    _LOGGER.info(
        'Creating %s servers in %s partition, min on-demand: %s, max: %s',
        count, partition, min_on_demand, max_on_demand
    )

    ec2_conn = awscontext.GLOBAL.ec2
    ipa_domain = awscontext.GLOBAL.ipa_domain

    admin_cell = context.GLOBAL.admin.cell()
    cell = context.GLOBAL.cell
    cell_data = admin_cell.get(cell)['data']

    admin_part = context.GLOBAL.admin.partition()
    try:
        _ldap_data = admin_part.get([partition, cell], dirty=True)
        partition_data = _ldap_data.get('data', {})
    except admin_exceptions.NoSuchObjectResult:
        partition_data = {}

    image_id = partition_data.get('image', cell_data['image'])
    cell_img_accounts = cell_data.get('image_accounts', [])
    image_accounts = partition_data.get('image_accounts',
                                        cell_img_accounts)
    if not image_accounts:
        image_accounts = []
    image_accounts.append('self')

    if not image_id.startswith('ami-'):
        image_id = ec2client.get_image(
            ec2_conn, owners=image_accounts, name=image_id
        )['ImageId']

    instance_type = partition_data.get('size', cell_data['size'])
    instance_types = partition_data.get(
        'instance_types', [instance_type]
    )
    spot_instance_types = partition_data.get(
        'spot_instance_types', instance_types
    )
    spot_duration = partition_data.get('spot_duration')
    subnets = partition_data.get('subnets', cell_data['subnets'])
    secgroup_id = partition_data.get('secgroup', cell_data['secgroup'])
    hostgroups = partition_data.get('hostgroups', cell_data['hostgroups'])
    instance_profile = partition_data.get(
        'instance_profile', cell_data['instance_profile']
    )
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

    hostnames = _generate_hostnames(
        ipa_domain, cell, partition, count,
        min_on_demand=min_on_demand,
        max_on_demand=max_on_demand
    )
    instance_types = _instance_types(
        instance_types, spot_instance_types
    )
    host_params = dict(
        image_id=image_id,
        count=1,
        disk=disk_size,
        domain=ipa_domain,
        key=None,
        secgroup_ids=secgroup_id,
        role='node',
        instance_vars=instance_vars,
        instance_profile=instance_profile,
        hostgroups=hostgroups,
        ip_address=None,
        eni=None,
        tags=tags,
        spot_duration=spot_duration,
        nshostlocation=nshostlocation,
    )
    if pool:
        func = functools.partial(
            _create_hosts_no_exc,
            instance_types=instance_types,
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
            hostnames, instance_types, subnets, cell, partition, **host_params
        )


@aws.profile
def delete_n_servers(count, partition=None, pool=None):
    """Delete old servers."""
    admin_srv = context.GLOBAL.admin.server()

    servers = admin_srv.list(
        {'cell': context.GLOBAL.cell, 'partition': partition}
    )
    hostnames = sorted([s['_id'] for s in servers])
    extra_servers = hostnames[0:count]

    delete_servers_by_name(extra_servers, pool=pool)


@aws.profile
def delete_servers_by_name(servers, pool=None):
    """Delete servers by name."""
    _LOGGER.info('Deleting servers: %r', servers)

    zkclient = context.GLOBAL.zk.conn
    for server in servers:
        try:
            presence.kill_node(zkclient, server)
        except kazoo.exceptions.NoNodeError:
            pass

    if pool:
        batches = _split_list(servers, pool.workers)
        for _res, err in pool.map(_delete_hosts_no_exc, batches):
            if err:
                raise err
    else:
        _delete_hosts(servers)


def _query_stateapi():
    state_api = context.GLOBAL.state_api()
    apps_state = restclient.get(state_api, _SCHEDULER_APPS_URL).json()
    servers_state = restclient.get(state_api, _SCHEDULER_SERVERS_URL).json()
    return apps_state, servers_state


def _get_state():
    apps_state, servers_state = _query_stateapi()
    admin_srv = context.GLOBAL.admin.server()
    zkclient = context.GLOBAL.zk.conn

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

    servers = admin_srv.list(
        {'cell': context.GLOBAL.cell},
        get_operational_attrs=True
    )
    try:
        blackedout_servers = set(zkclient.get_children(z.BLACKEDOUT_SERVERS))
    except kazoo.client.NoNodeError:
        blackedout_servers = set()

    for server in servers:
        server_name = server['_id']
        server_data = server.get('data', {})
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

        if server_name in blackedout_servers:
            server_state = 'blackedout'

        servers_by_partition[server['partition']].append({
            'name': server_name,
            'state': server_state,
            'create_timestamp': server_create_timestamp,
            'num_apps': num_apps_by_server[server_name],
            'lifecycle': server_data.get('lifecycle', 'on-demand'),
        })

        if server_state in ('blackedout', 'frozen'):
            _LOGGER.warning('Server %s is %s', server_name, server_state)

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


def _select_extra_servers(servers, state, idle_ttl=0, max_extra_servers=None):
    extra_servers = []
    for server in servers:
        if max_extra_servers is not None:
            if len(extra_servers) == max_extra_servers:
                return extra_servers

        if server['num_apps']:
            continue

        if server['state'] not in state:
            continue

        if idle_ttl and time.time() - server['idle_since'] <= idle_ttl:
            continue

        extra_servers.append(server['name'])
    return extra_servers


def _scale_partition(server_app_ratio, idle_server_ttl,
                     min_servers, max_servers, max_broken_servers,
                     apps, servers):
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
            servers, ('up'), idle_server_ttl, max_extra_servers
        )
    extra_servers += _select_extra_servers(servers, ('down'))
    extra_servers += _select_extra_servers(
        servers, ('blackedout', 'frozen')
    )[max_broken_servers:]
    _LOGGER.info('Empty servers to delete: %r', extra_servers)

    return new_servers, extra_servers


def _update_idle_since(idle_servers_tracker, servers):
    idle_servers = set()

    for server in servers:
        if server['num_apps'] == 0:
            idle_servers_tracker.setdefault(server['name'], time.time())
            server['idle_since'] = idle_servers_tracker[server['name']]
            idle_servers.add(server['name'])

    for server_name in list(idle_servers_tracker):
        if server_name not in idle_servers:
            idle_servers_tracker.pop(server_name, None)


def scale(default_server_app_ratio, default_idle_server_ttl,
          pool=None,
          idle_servers_tracker=None):
    """Autoscale cell capacity."""
    _LOGGER.info('Getting cell state')
    apps_by_partition, servers_by_partition = _get_state()

    _LOGGER.info('Getting cell partitions')
    cell = context.GLOBAL.admin.cell().get(context.GLOBAL.cell)

    if idle_servers_tracker is None:
        idle_servers_tracker = collections.defaultdict(dict)

    for partition in cell['partitions']:
        partition_name = partition['_id']
        try:
            autoscale_conf = partition['data']['autoscale']
        except KeyError:
            autoscale_conf = None

        if not autoscale_conf:
            continue

        try:
            _LOGGER.info('Scaling partition %s: %r',
                         partition_name, autoscale_conf)

            min_servers = autoscale_conf['min_servers']
            max_servers = autoscale_conf['max_servers']
            max_broken_servers = autoscale_conf.get('max_broken_servers', 0)
            max_on_demand_servers = autoscale_conf.get('max_on_demand_servers')
            server_app_ratio = float(
                autoscale_conf.get(
                    'server_app_ratio', default_server_app_ratio
                )
            )
            idle_server_ttl = autoscale_conf.get(
                'idle_server_ttl', default_idle_server_ttl
            )

            apps = apps_by_partition.get(partition_name, [])
            servers = servers_by_partition.get(partition_name, [])

            _update_idle_since(idle_servers_tracker[partition_name], servers)

            new_servers, extra_servers = _scale_partition(
                server_app_ratio, idle_server_ttl,
                min_servers, max_servers, max_broken_servers,
                apps, servers
            )

            if new_servers > 0:
                if max_on_demand_servers is None:
                    create_n_servers(new_servers, partition_name, pool=pool)
                else:
                    curr_cnt = len([
                        server for server in servers
                        if server['lifecycle'] == 'on-demand'
                    ])
                    _LOGGER.info('Current on-demand servers: %d', curr_cnt)
                    min_on_demand = max(0, min_servers - curr_cnt)
                    max_on_demand = max(0, max_on_demand_servers - curr_cnt)
                    create_n_servers(
                        new_servers, partition_name,
                        min_on_demand=min_on_demand,
                        max_on_demand=max_on_demand,
                        pool=pool
                    )
            if extra_servers:
                delete_servers_by_name(extra_servers, pool=pool)
        except ExpiredCredentialsError:
            raise
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception('Error while scaling partition %s: %r',
                              partition_name, err)

    return idle_servers_tracker
