""" IPA client connectors and helper functions """
import logging

import requests
import requests_kerberos

from treadmill import dnsutils

from treadmill_aws import noproxy


_LOGGER = logging.getLogger(__name__)
_KERBEROS_AUTH = requests_kerberos.HTTPKerberosAuth()
_API_VERSION = '2.28'
_DEFAULT_TTL = 5


def get_ipa_urls_from_dns(domain):
    """Looks up IPA servers from DNS SRV records.
    """
    ipa_srv_rec = dnsutils.srv('_kerberos._tcp.{}'.format(domain))
    if not ipa_srv_rec:
        raise Exception('No IPA servers found')

    # Sort by (priority, -weight).
    ipa_srv_rec.sort(key=lambda srv_rec: (srv_rec[2], -srv_rec[3]))

    _LOGGER.debug('IPA SRV records: %r', ipa_srv_rec)

    return [
        'https://{}/ipa'.format(srv_rec[0])
        for srv_rec in ipa_srv_rec
    ]


# From IPA documentation:
#
# https://github.com/freeipa/freeipa/blob/master/ipalib/errors.py
#
# The public errors are arranging into five main blocks of error code ranges:
#     =============  ========================================
#      Error codes                 Exceptions
#     =============  ========================================
#     1000 - 1999    `AuthenticationError` and its subclasses
#     2000 - 2999    `AuthorizationError` and its subclasses
#     3000 - 3999    `InvocationError` and its subclasses
#     4000 - 4999    `ExecutionError` and its subclasses
#     5000 - 5999    `GenericError` and its subclasses
#     =============  ========================================
#
# We will copy ranges with similar exception hierarchy, with explicit support
# for code 4002 (DuplicateEntry) and 4001 (NotFound)

class IPAError(Exception):
    """IPA Client exceptions."""
    pass


class AuthenticationError(IPAError):
    """IPA Client authentication errors."""
    pass


class AuthorizationError(IPAError):
    """IPA Client authorization errors."""
    pass


class InvocationError(IPAError):
    """IPA Client invocation errors."""
    pass


class ExecutionError(IPAError):
    """IPA Client execution errors."""
    pass


class NotFoundError(ExecutionError):
    """Entry not found error."""
    pass


class AlreadyExistsError(ExecutionError):
    """Entry already exists."""
    pass


class GenericError(IPAError):
    """IPA generic error."""
    pass


def check_response(response):
    """Check response does not contain errors."""
    if response.status_code == 401 and not response.text:
        raise AuthenticationError('Authentication has failed')

    # FreeIPA returns an HTML document rather than JSON if creds not valid:
    if 'Unable to verify your Kerberos credentials' in response.text:
        raise AuthenticationError('Invalid Kerberos Credentials')

    response_obj = response.json()

    if response_obj['result']:
        # Only search results contain 'truncated' key:
        if response_obj['result'].get('truncated', False):
            raise IPAError('IPA results truncated.')

    if not response_obj['error']:
        return

    err = response_obj['error']
    code = err['code']
    if 1000 <= code <= 1999:
        raise AuthenticationError(err['message'])
    if 2000 <= code <= 2999:
        raise AuthorizationError(err['message'])
    if 3000 <= code <= 3999:
        raise InvocationError(err['message'])
    if code == 4001:
        raise NotFoundError(err['message'])
    if code == 4002:
        raise AlreadyExistsError(err['message'])
    if 4000 <= code <= 4999:
        raise ExecutionError(err['message'])
    if 5000 <= code <= 5999:
        raise GenericError(err['message'])

    raise IPAError('Unknown error.')


# TODO: Error handling is very inconsistent, need to be rewritten.
class IPAClient():
    """ Interfaces with freeIPA API to add, delete, list and manage
        IPA hosts, users and groups.

    """

    def __init__(self, certs, domain):
        self.certs = certs
        self.domain = domain
        self.ipa_urls = get_ipa_urls_from_dns(self.domain)

    def _post(self, payload=None, auth=_KERBEROS_AUTH):
        for ipa_url in self.ipa_urls:
            try:
                return self._post_request(ipa_url, payload=payload, auth=auth)
            except requests.exceptions.ConnectionError:
                _LOGGER.exception('Connection error: %s, trying next', ipa_url)
        raise Exception('Connection error: %r' % self.ipa_urls)

    def _post_request(self, ipa_url, payload=None, auth=_KERBEROS_AUTH):
        """ Submits formatted JSON to IPA server.
            Uses requests_kerberos module for Kerberos authentication with IPA.
        """
        with noproxy.NoProxy() as _proxy:
            response = requests.post('{}/session/json'.format(ipa_url),
                                     json=payload,
                                     auth=auth,
                                     headers={'referer': ipa_url},
                                     proxies={'http': None, 'https': None},
                                     verify=self.certs)

        check_response(response)
        return response

    def enroll_host(self, hostname, **kwargs):
        """Enroll new host with IPA server.
        """
        options = {'force': True,
                   'random': True,
                   'version': _API_VERSION}
        options.update(kwargs)
        payload = {'method': 'host_add',
                   'params': [[hostname], options],
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

    def get_hosts(self, pattern=None, **kwargs):
        """Retrieve host records from IPA server.
        """
        options = {'version': _API_VERSION, 'sizelimit': 0}
        options.update(kwargs)
        payload = {'method': 'host_find',
                   'params': [[pattern], options],
                   'id': 0}
        resp = self._post(payload=payload).json()

        # Return flat list of FQDN results
        return [result
                for hosts in resp['result']['result']
                for result in hosts['fqdn']]

    def add_dns_record(self, record_type, record_name, record_value,
                       ttl=_DEFAULT_TTL):
        """Add new DNS record to IPA server.
        """
        payload = {'method': 'dnsrecord_add',
                   'params': [[self.domain, record_name],
                              {record_type: record_value,
                               'dnsttl': ttl,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def delete_dns_record(self,
                          record_type,
                          record_name,
                          record_value,
                          dns_zone=None):
        """Delete DNS record from IPA server.
        """
        if not dns_zone:
            dns_zone = self.domain

        payload = {'method': 'dnsrecord_del',
                   'params': [[dns_zone, record_name],
                              {record_type: record_value,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def force_delete_dns_record(self, record_name, record_zone):
        """Delete all DNS records matching record name from IPA server.
        """
        payload = {'method': 'dnsrecord_del',
                   'params': [[record_zone, record_name],
                              {'del_all': True,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def search_dns_record(self, idnsname=None):
        """Retrieve DNS records from IPA server.
        """
        if idnsname:
            payload = {'method': 'dnsrecord_find',
                       'params': [[self.domain, idnsname],
                                  {'version': _API_VERSION,
                                   'sizelimit': 0}],
                       'id': 0}
        else:
            payload = {'method': 'dnsrecord_find',
                       'params': [[self.domain],
                                  {'version': _API_VERSION,
                                   'sizelimit': 0}],
                       'id': 0}
        return self._post(payload=payload).json()

    def get_dns_record(self, idnsname):
        """Retrieve DNS records from IPA server.
        """
        payload = {'method': 'dnsrecord_show',
                   'params': [[self.domain, idnsname],
                              {'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def add_srv_record(self, idnsname, host, port, weight=0, priority=0,
                       ttl=_DEFAULT_TTL):
        """Add SRV record."""
        record = '{weight} {priority} {port} {host}'.format(
            weight=weight,
            priority=priority,
            port=port,
            host=host,
        )
        _LOGGER.debug(
            'Adding SRV record: %s %s, ttl=%s', idnsname, record, ttl
        )
        self.add_dns_record(
            record_type='srvrecord',
            record_name=idnsname,
            record_value=record,
            ttl=ttl
        )

    def delete_srv_record(self, idnsname, host, port, weight=0, priority=0):
        """Add SRV record."""
        record = '{weight} {priority} {port} {host}'.format(
            weight=weight,
            priority=priority,
            port=port,
            host=host
        )
        _LOGGER.debug('Deleting SRV record: %s %s', idnsname, record)
        self.delete_dns_record(
            record_type='srvrecord',
            record_name=idnsname,
            record_value=record
        )

    def add_txt_record(self, idnsname, record, ttl=_DEFAULT_TTL):
        """Add TXT record."""
        _LOGGER.debug('Adding TXT record: %s %s', idnsname, record)
        self.add_dns_record(
            record_type='txtrecord',
            record_name=idnsname,
            record_value=record,
            ttl=ttl
        )

    def delete_txt_record(self, idnsname, record):
        """Delete TXT record."""
        _LOGGER.debug('Adding TXT record: %s %s', idnsname, record)
        self.delete_dns_record(
            record_type='txtrecord',
            record_name=idnsname,
            record_value=record
        )

    def add_ptr_record(
            self,
            record_zone,
            record_type,
            record_name,
            record_value,
            ttl=_DEFAULT_TTL):
        """Add new PTR record to IPA DNS server. """
        payload = {'method': 'dnsrecord_add',
                   'params': [[record_zone, record_name],
                              {record_type: record_value,
                               'dnsttl': ttl,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def delete_ptr_record(
            self,
            record_zone,
            record_type,
            record_name,
            record_value):
        """Delete PTR record from IPA DNS server."""
        payload = {'method': 'dnsrecord_del',
                   'params': [[record_zone, record_name],
                              {record_type: record_value,
                               'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def add_user(self, user_name, first_name, last_name, user_type):
        """Add new user to IPA server.
        """
        payload = {'method': 'user_add',
                   'params': [[user_name],
                              {'givenname': first_name,
                               'sn': last_name,
                               'userclass': user_type,
                               'version': _API_VERSION}],
                   'id': 0}
        response = self._post(payload=payload)
        return response.json()['result']['result']

    def delete_user(self, user_name):
        """Remove user from IPA server.
        """
        payload = {'method': 'user_del',
                   'params': [[user_name],
                              {'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()

    def list_users(self, pattern=None):
        """Retrieve user records from IPA server.
        """
        # TODO: is this really needed?
        if pattern is None:
            pattern = ''

        if pattern:
            payload = {'method': 'user_find',
                       'params': [[pattern],
                                  {'version': _API_VERSION,
                                   'sizelimit': 0}],
                       'id': 0}
        else:
            payload = {'method': 'user_find',
                       'params': [[],
                                  {'version': _API_VERSION,
                                   'sizelimit': 0}],
                       'id': 0}
        return self._post(payload=payload).json()['result']['result']

    def show_user(self, user_name):
        """Show details about IPA user.
        """
        payload = {'method': 'user_show',
                   'params': [[user_name],
                              {'version': _API_VERSION}],
                   'id': 0}
        return self._post(payload=payload).json()['result']['result']

    def hostgroup_add_member(self, hostgroup, host):
        """Add host to IPA hostgroup.
        """
        payload = {'method': 'hostgroup_add_member',
                   'params': [[hostgroup],
                              {'host': host,
                               'version': _API_VERSION}],
                   'id': 0}
        response = self._post(payload=payload)
        return response.json()['result']['result']
