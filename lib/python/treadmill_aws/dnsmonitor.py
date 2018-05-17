""" ZK to IPA DNS watch/update daemon and helper functions """

import logging
import os
import re
from treadmill.dirwatch import DirWatcher
from treadmill_aws.ipaclient import filter_raw_records

_LOGGER = logging.getLogger(__name__)

DEFAULT_WEIGHT = 10
DEFAULT_PRIORITY = 10


def find_app_dns(ipaclient, server, protocol, app_name):
    """Returns a list of SRV records in dictionary format matching app_name.
    """
    idnsname = '_{server}._{protocol}.{app_name}.{domain}'.format(
        server=server,
        protocol=protocol,
        app_name=app_name,
        domain=ipaclient.domain)

    _LOGGER.debug('Generated idnsname: %s', idnsname)

    return ipaclient.get_dns_record(idnsname=idnsname)


def generate_srv_record(cell_name, server, app_name, protocol, endpoints):
    """Generates SRV DNS records to send to IPA.
    """

    host, port = endpoints[0]
    idnsname = '_{server}._{protocol}.{app_name}.{cell_name}'.format(
        app_name=app_name,
        cell_name=cell_name,
        protocol=protocol,
        server=server)

    record = '{weight} {priority} {port} {host}.'.format(
        weight=DEFAULT_WEIGHT,
        priority=DEFAULT_PRIORITY,
        port=port,
        host=host)

    dns_record = {'type': 'srvrecord',
                  'idnsname': idnsname,
                  'record': record}

    _LOGGER.debug('Generated DNS record: %s', dns_record)
    return dns_record


def get_filesystem_context(endpoint_dir, path):
    """ Returns dict representing file in ZK.
    """

    proid, file_name = path.split('/')[-2:]
    proid_dir = '{path}/{proid}'.format(path=endpoint_dir, proid=proid)

    app, protocol, server = re.search(
        r'([a-z0-9-]+)#\d*:(\w+):(\w+)', file_name).groups()

    return {'app': app,
            'file_name': file_name,
            'proid_dir': proid_dir,
            'protocol': protocol,
            'server': server}


def get_zk_target_from_file(path):
    """ Returns host and port from Zookeeper mirror on disk.
    """
    with open(path) as f:
        hostname, port = f.read().split(':')
    return hostname, int(port)


def mirror_zookeeper(cell_name, ipaclient, zk_records):
    """This function gets a list of records from Zookeeper and from IPA
       DNS, generates an index of each record list, then adds any new
       records & deletes any old records by comparing each list against
       the other's index.
    """
    raw_records = ipaclient.get_dns_record()
    ipa_records = filter_raw_records(cell_name=cell_name,
                                     raw_records=raw_records,
                                     record_type='srvrecord')

    zk_record_list = [z['record'] for z in zk_records]
    ipa_record_list = [i['record'] for i in ipa_records]

    # Add new records from Zookeeper
    for z_rec in zk_records:
        if z_rec['record'] not in ipa_record_list:
            _LOGGER.debug('Add record: %s', z_rec)
            ipaclient.add_dns_record(record_type='srvrecord',
                                     record_name=z_rec['idnsname'],
                                     record_value=z_rec['record'])

    # Delete bad records in IPA DNS
    for i_rec in ipa_records:
        if i_rec['record'] not in zk_record_list:
            _LOGGER.debug('Delete record: %s', i_rec)
            ipaclient.delete_dns_record(record_type='srvrecord',
                                        record_name=i_rec['idnsname'],
                                        record_value=i_rec['record'])


class DNSMonitor():
    """Class to monitor ZK directory and reflect changes to IPA DNS records.
    """

    def __init__(self, cell_name, ipaclient, zkfs_dir):
        """ Environment setup. """
        _LOGGER.info('Montoring directory: %s', zkfs_dir)
        self.cell_name = cell_name
        self.endpoint_dir = zkfs_dir
        self.ipaclient = ipaclient
        self.on_created = self._on_created
        self.on_deleted = self._on_deleted

    def _on_created(self, path):
        """ Executes on creation of new ZK endpoint """
        context = get_filesystem_context(endpoint_dir=self.endpoint_dir,
                                         path=path)
        _LOGGER.info('Found new endpoint %s/%s',
                     context['proid_dir'],
                     context['file_name'])

        # Get list of endpoints from new ZK entry
        endpoints = [get_zk_target_from_file(path=path)]

        # Create DNS entries for new endpoints
        dns_record = generate_srv_record(cell_name=self.cell_name,
                                         server=context['server'],
                                         app_name=context['app'],
                                         protocol=context['protocol'],
                                         endpoints=endpoints)

        # Submit DNS record to freeIPA
        self.ipaclient.add_dns_record(record_type='srvrecord',
                                      record_name=dns_record['idnsname'],
                                      record_value=dns_record['record'])
        _LOGGER.info('Record added: %s', path)

    def _on_deleted(self, path):
        """Executes on deletion of existing ZK endpoint.
        """
        _LOGGER.info('Record deleted: %s', path)
        self.sync()

    def run(self):
        """Start daemon. Run initial sync, then watch for changes.
        """
        watch = DirWatcher()
        watch.on_created = self._on_created
        watch.on_deleted = self._on_deleted
        watch.add_dir(self.endpoint_dir)

        # Run an initial sync when daemon starts
        self.sync()

        # Main loop
        while True:
            if watch.wait_for_events(5):
                watch.process_events()

    def sync(self):
        """Generate list of DNS records derived from ZK filesystem mirror,
           then mirror them to freeIPA's DNS.
        """
        mirror_list = []
        zk_context = []

        # Generate list of app endpoints owned by proid
        app_full_paths = ['{path}/{app}'.format(path=self.endpoint_dir,
                                                app=app)
                          for app in os.listdir(self.endpoint_dir)]

        # Generate app context and endpoints for each discovered app
        for path in app_full_paths:
            context = get_filesystem_context(endpoint_dir=self.endpoint_dir,
                                             path=path)
            endpoints = [get_zk_target_from_file(path=path)]

            if context and endpoints:
                zk_context.append({'context': context,
                                   'endpoints': endpoints})

        # Generate DNS record for each app
        for app in zk_context:
            rec = generate_srv_record(cell_name=self.cell_name,
                                      server=app['context']['server'],
                                      app_name=app['context']['app'],
                                      protocol=app['context']['protocol'],
                                      endpoints=app['endpoints'])
            if rec:
                mirror_list.append(rec)

        mirror_zookeeper(cell_name=self.cell_name,
                         ipaclient=self.ipaclient,
                         zk_records=mirror_list)
