""" IPA client connectors and helper functions """
import logging
import random
import dns.resolver
import requests
import requests_kerberos

_LOGGER = logging.getLogger(__name__)
_KERBEROS_AUTH = requests_kerberos.HTTPKerberosAuth()
_API_VERSION = '2.28'


def get_ipa_server_from_dns(domain):
    """Looks up random IPA server from DNS SRV records.
    """
    raw_results = [
        result.to_text() for result in
        dns.resolver.query('_kerberos._tcp.{}'.format(domain),
                           'SRV')]
    if raw_results:
        return random.choice(raw_results).split()[-1]
    else:
        raise Exception('No IPA Servers Found')


def filter_raw_records(cell_name, raw_records, record_type):
    """Extract and filter cell-specific typed records from IPA JSON export.
       Returns list of dict objects that describe matching records.
    """
    dns_records = []

    # Extract individual entries from record dump that match type, cell_name
    for record in [fmt_rec for fmt_rec in raw_records['result']['result']
                   if cell_name in fmt_rec['idnsname'][0] and record_type in
                   fmt_rec.keys()]:

        # IPA returns multiple records with the same idnsname
        # as type List, and returns singleton records as type String
        if isinstance(record[record_type], list):
            for entry in record[record_type]:
                dns_records.append({'type': record_type,
                                    'dn': record['dn'],
                                    'idnsname': record['idnsname'][0],
                                    'record': entry})
        else:
            dns_records.append({'type': record_type,
                                'dn': record['dn'],
                                'idnsname': record['idnsname'][0],
                                'record': record[record_type]})
    return dns_records


class IPAClient():
    """Interfaces with freeIPA API to register and deregister hosts.
    """

    def __init__(self, certs, domain):
        self.certs = certs
        self.domain = domain

        # Strip trailing period as it breaks SSL
        self.ipa_server_hostn = get_ipa_server_from_dns(self.domain)[:-1]
        self.ipa_srv_address = 'https://{}/ipa'.format(self.ipa_server_hostn)
        self.ipa_srv_api_address = '{}/session/json'.format(
            self.ipa_srv_address)
        self.referer = {'referer': self.ipa_srv_address}

    def _post(self, payload=None, auth=_KERBEROS_AUTH):
        """ Submits formatted JSON to IPA server.
            Uses requests_kerberos module for Kerberos authentication with IPA.
        """
        response = requests.post(self.ipa_srv_api_address,
                                 json=payload,
                                 auth=auth,
                                 headers=self.referer,
                                 verify=self.certs)

        # FreeIPA returns an HTML document rather than JSON if creds not valid:
        if 'Unable to verify your Kerberos credentials' in response.text:
            raise Exception('Invalid Kerberos Credentials')

        if response.json()['error']:
            raise KeyError(response.json()['error']['message'])

        return response

    def enroll_host(self, hostname):
        """Enroll new host with IPA server.
        """
        payload = {'method': 'host_add',
                   'params': [[hostname],
                              {'force': True,
                               'random': True,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def unenroll_host(self, hostname):
        """Unenroll host from IPA server."""
        payload = {'method': 'host_del',
                   'params': [[hostname],
                              {'updatedns': True,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def get_hosts(self, pattern=None):
        """Retrieve host records from IPA server.
        """
        payload = {'method': 'host_find',
                   'params': [[pattern],
                              {'version': _API_VERSION}],
                   'id': 0}
        resp = self._post(payload=payload).json()

        # Return flat list of FQDN results
        return [result
                for hosts in resp['result']['result']
                for result in hosts['fqdn']]

    def add_dns_record(self, record_type, record_name, record_value):
        """Add new DNS record to IPA server.
        """
        payload = {'method': 'dnsrecord_add',
                   'params': [[self.domain, record_name],
                              {record_type: record_value,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def del_dns_record(self, record_type, record_name, record_value):
        """Delete DNS record from IPA server.
        """
        payload = {'method': 'dnsrecord_del',
                   'params': [[self.domain, record_name],
                              {record_type: record_value,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def get_dns_record(self, idnsname=None):
        """Retrieve DNS records from IPA server.
        """
        if idnsname:
            payload = {'method': 'dnsrecord_find',
                       'params': [[self.domain, idnsname],
                                  {'version': _API_VERSION}],
                       'id': 0}
        else:
            payload = {'method': 'dnsrecord_find',
                       'params': [[self.domain],
                                  {'version': _API_VERSION}],
                       'id': 0}
        return self._post(payload=payload).json()
