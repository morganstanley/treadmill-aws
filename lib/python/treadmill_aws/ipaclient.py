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
    """ Looks up random IPA server from DNS SRV records """
    raw_results = [
        result.to_text() for result in
        dns.resolver.query('_kerberos._tcp.{}'.format(domain),
                           'SRV')]
    return random.choice(raw_results).split()[-1]


class IPAClient():
    """ Interfaces with freeIPA API to register and deregister hosts """

    def __init__(self, domain, certs):
        self.domain = domain
        self.certs = certs
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
        if response.json()['error']:
            raise KeyError(response.json()['error']['message'])

        return response

    def enroll_ipa_host(self, hostname):
        """ Enroll new host with IPA server """
        payload = {'method': 'host_add',
                   'params': [[hostname],
                              {'force': True,
                               'random': True,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def unenroll_ipa_host(self, hostname):
        """ Unenroll host from IPA server """
        payload = {'method': 'host_del',
                   'params': [[hostname],
                              {'updatedns': True,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def get_ipa_hosts(self, pattern=''):
        """ Retrieve host records from IPA server """
        payload = {'method': 'host_find',
                   'params': [[pattern],
                              {'version': _API_VERSION}],
                   'id': 0}
        resp = self._post(payload=payload).json()

        # Return flat list of FQDN results
        return [result
                for hosts in resp['result']['result']
                for result in hosts['fqdn']]
