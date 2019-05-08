"""Syncronize DNS data with Zookeeper file system mirror.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import glob
import io
import logging
import os
import socket

from treadmill import utils
from treadmill import yamlwrapper as yaml


_LOGGER = logging.getLogger(__name__)

DEFAULT_WEIGHT = 10
DEFAULT_PRIORITY = 10


class DnsSync:
    """Syncronizes DNS with Zk mirror on disk."""

    def __init__(self, ipaclient, cell, zone, fs_root, scopes):
        self.ipaclient = ipaclient
        self.cell = cell
        self.fs_root = os.path.realpath(fs_root)

        self.state = None
        self.servers = set()
        self.scopes = {
            'cell': cell,
            'global': None,
        }
        self.scopes.update(scopes)
        self.zone = zone

    def _srv_rsrc(self, name, scope, proto, endpoint, hostport):
        """Return tuple of resource endpoint/payload."""
        if proto not in ['tcp', 'udp']:
            _LOGGER.warning('Unsupported proto: %s', proto)
            return None

        if scope not in self.scopes:
            _LOGGER.warning('Unsupported scope: %s', scope)
            return None

        host, port = hostport.split(':')
        if scope == 'global':
            zone = None
            srv_rec = '_{endpoint}._{proto}.{name}'
        else:
            zone = '.'.join([self.scopes[scope], scope])
            srv_rec = '_{endpoint}._{proto}.{name}.{zone}'

        return (
            srv_rec.format(
                endpoint=endpoint,
                proto=proto,
                name=name,
                zone=zone),
            '{weight} {priority} {port} {host}.'.format(
                weight=DEFAULT_WEIGHT,
                priority=DEFAULT_PRIORITY,
                port=port,
                host=host
            )
        )

    def _current_records(self):
        """Return all records found in DNS for the given cell."""
        all_records = self.ipaclient.list_dns_records(dns_zone=self.zone)
        current = set()
        for rec in all_records:
            if 'srvrecord' not in rec:
                continue

            srv_rec_name = rec['idnsname'][0]

            for srv_rec in rec['srvrecord']:
                _wei, _prio, port, host = srv_rec.split()

                # There is no way to tell if the old record pointing to host
                # that is no longer there belonged to the cell. There is no
                # point keeping srv records pointing to hosts that no longer
                # exist, so we GC for everyone.
                try:
                    socket.gethostbyname(host)
                except socket.error:
                    _LOGGER.info(
                        'Stale record - host does not exist: %s %s:%s',
                        srv_rec_name,
                        host,
                        port
                    )
                    current.add((srv_rec_name, srv_rec))
                    continue

                # skip records that do not belong to the cell.
                host = host.rstrip('.')
                if host not in self.servers:
                    _LOGGER.debug('Skip non-cell record: %s %s:%s',
                                  srv_rec_name, host, port)
                    continue

                current.add((srv_rec_name, srv_rec))

        return current

    def _srv_records(self, alias, scope, pattern, endpoint):
        """Return srv records matched by pattern."""
        result = set()

        proid, app_pattern = pattern.split('.', 1)
        glob_pattern = os.path.join(self.fs_root, 'endpoints', proid,
                                    app_pattern + '#[0-9]*:*:' + endpoint)
        matching = glob.glob(glob_pattern)
        _LOGGER.debug('matching: %r', matching)

        for match in matching:
            _app, proto, _endpoint = match.split(':')
            try:
                with io.open(match) as f:
                    hostport = f.read()
                    srv_rec_rsrc = self._srv_rsrc(alias, scope, proto,
                                                  endpoint, hostport)
                    if srv_rec_rsrc:
                        result.add(srv_rec_rsrc)
            except IOError:
                _LOGGER.info('Endpoint removed: %s', match)

        return result

    def _match_appgroup(self, appgroup):
        """For all endpoints that match the appgroup, add to target state."""
        _LOGGER.debug('appgroup: %r', appgroup)
        if appgroup['group-type'] != 'dns':
            return set()

        data = utils.equals_list2dict(appgroup.get('data'))
        _LOGGER.debug('data: %r', data)
        # Top level API must ensure that alias is always set, even it user
        # selects app pattern as alias (default).
        alias = data.get('alias')
        if not alias:
            _LOGGER.error('No alias supplied for %r', appgroup)
            return set()

        scope = data.get('scope', 'cell')

        result = set()
        for endpoint in appgroup['endpoints']:
            srvs = self._srv_records(
                alias, scope, appgroup['pattern'], endpoint
            )
            _LOGGER.debug('srvs: %r', srvs)
            result.update(srvs)

        return result

    def _target_records(self):
        """Returns target state as defined by zk mirror on file system."""
        target_records = set()
        appgroups_pattern = os.path.join(self.fs_root, 'app-groups', '*')
        for appgroup_f in glob.glob(appgroups_pattern):
            _LOGGER.debug('appgroup_f: %r', appgroup_f)
            if appgroup_f.startswith('.'):
                continue
            try:
                with io.open(appgroup_f) as f:
                    appgroup = yaml.load(stream=f)
                    target_records.update(self._match_appgroup(appgroup))
            except IOError:
                _LOGGER.info('Appgroup deleted: %s', appgroup_f)

        _LOGGER.debug('target_records: %r', target_records)
        return target_records

    def _update_cell_servers(self):
        """Update list of servers that belong to the cell."""
        servers_glob = glob.glob(os.path.join(self.fs_root, 'servers', '*'))
        self.servers = set(map(os.path.basename, servers_glob))

        _LOGGER.debug('Cell servers:')
        for server in sorted(self.servers):
            _LOGGER.debug('%s', server)

    def sync(self):
        """Syncronizes current and target state."""
        self._update_cell_servers()

        if self.state is None:
            self.state = self._current_records()

        _LOGGER.debug('Current state:')
        for record in sorted(self.state):
            _LOGGER.debug('%r', record)

        target = self._target_records()

        _LOGGER.debug('Target state:')
        for record in sorted(target):
            _LOGGER.debug('%r', record)

        extra = self.state - target
        missing = target - self.state

        if not (extra or missing):
            _LOGGER.info('DNS is up to date.')

        for idnsname, record in extra:
            _LOGGER.info('del: %s %s', idnsname, record)
            self.ipaclient.delete_dns_record('srvrecord', idnsname, record)

        for idnsname, record in missing:
            _LOGGER.info('add: %s %s', idnsname, record)
            self.ipaclient.add_dns_record('srvrecord', idnsname, record)

        self.state = target
