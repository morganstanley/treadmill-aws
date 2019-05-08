"""FreeIPA API wrapper to manage IPA hosts, dns records and users."""

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
    """Looks up IPA servers from DNS SRV records."""
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


class IPAClient:
    """FreeIPA API wrapper to manage IPA hosts, dns records and users."""

    def __init__(self, certs, domain):
        self.certs = certs
        self.domain = domain
        self.ipa_urls = get_ipa_urls_from_dns(self.domain)

    def _call(self, method_name, args, options=None):
        """Format JSON payload and submit it to IPA server.
           Try different IPA server on connection error.
        """
        if not options:
            options = {}

        if 'version' not in options:
            options['version'] = _API_VERSION

        payload = {
            'method': method_name,
            'params': [args, options],
            'id': 0,
        }

        for ipa_url in self.ipa_urls:
            try:
                return self._post(ipa_url, payload)
            except requests.exceptions.ConnectionError:
                _LOGGER.exception('Connection error: %s, trying next', ipa_url)
        raise Exception('Connection error: %r' % self.ipa_urls)

    def _post(self, ipa_url, payload):
        """Submit formatted JSON payload to IPA server and check response.
           Uses requests_kerberos module for Kerberos authentication with IPA.
        """
        with noproxy.NoProxy() as _proxy:
            response = requests.post(
                '{}/session/json'.format(ipa_url),
                json=payload,
                auth=_KERBEROS_AUTH,
                headers={'referer': ipa_url},
                proxies={'http': None, 'https': None},
                verify=self.certs
            )

        check_response(response)
        return response.json()['result']

    def enroll_host(self, hostname, **kwargs):
        """Enroll new host with IPA server."""
        args = [hostname]
        options = {'force': True, 'random': True}
        options.update(kwargs)
        return self._call('host_add', args, options)['result']

    def unenroll_host(self, hostname):
        """Unenroll host from IPA server."""
        args = [hostname]
        options = {'updatedns': True}
        return self._call('host_del', args, options)['result']

    def hostgroup_add_member(self, hostgroup, host):
        """Add host to IPA hostgroup."""
        args = [hostgroup]
        options = {'host': host}
        return self._call('hostgroup_add_member', args, options)['result']

    def list_hosts(self, pattern=None, **kwargs):
        """Retrieve host records from IPA server."""
        args = [pattern] if pattern else []
        options = {'sizelimit': 0}
        options.update(kwargs)
        result = self._call('host_find', args, options)
        # Return flat list of FQDN results.
        return [fqdn for hosts in result['result'] for fqdn in hosts['fqdn']]

    def list_dns_zones(self, pattern=None):
        """Retrieve DNS zone records from IPA server."""
        args = [pattern] if pattern else []
        options = {'sizelimit': 0}
        return self._call('dnszone_find', args, options)['result']

    def add_dns_record(self, record_type, idnsname, record, dns_zone=None,
                       ttl=_DEFAULT_TTL):
        """Add new DNS record to IPA server."""
        dns_zone = dns_zone or self.domain
        args = [dns_zone, idnsname]
        options = {record_type: record, 'dnsttl': ttl}
        return self._call('dnsrecord_add', args, options)['result']

    def delete_dns_record(self, record_type, idnsname, record, dns_zone=None):
        """Delete DNS record from IPA server."""
        dns_zone = dns_zone or self.domain
        args = [dns_zone, idnsname]
        options = {record_type: record}
        return self._call('dnsrecord_del', args, options)['result']

    def force_delete_dns_record(self, idnsname, dns_zone=None):
        """Delete all DNS records matching record name from IPA server."""
        dns_zone = dns_zone or self.domain
        args = [dns_zone, idnsname]
        options = {'del_all': True}
        return self._call('dnsrecord_del', args, options)['result']

    def list_dns_records(self, pattern=None, dns_zone=None):
        """Retrieve DNS records from IPA server."""
        dns_zone = dns_zone or self.domain
        args = [dns_zone, pattern] if pattern else [dns_zone]
        options = {'sizelimit': 0}
        return self._call('dnsrecord_find', args, options)['result']

    def get_dns_record(self, idnsname):
        """Show details about DNS record from IPA user."""
        args = [self.domain, idnsname]
        return self._call('dnsrecord_show', args)['result']

    def add_srv_record(self, idnsname, host, port, weight=0, priority=0,
                       ttl=_DEFAULT_TTL):
        """Add SRV record."""
        record = '{weight} {priority} {port} {host}'.format(
            weight=weight, priority=priority, port=port, host=host
        )
        return self.add_dns_record('srvrecord', idnsname, record, ttl=ttl)

    def delete_srv_record(self, idnsname, host, port, weight=0, priority=0):
        """Delete SRV record."""
        record = '{weight} {priority} {port} {host}'.format(
            weight=weight, priority=priority, port=port, host=host
        )
        return self.delete_dns_record('srvrecord', idnsname, record)

    def add_txt_record(self, idnsname, record, ttl=_DEFAULT_TTL):
        """Add TXT record."""
        return self.add_dns_record('txtrecord', idnsname, record, ttl=ttl)

    def delete_txt_record(self, idnsname, record):
        """Delete TXT record."""
        return self.delete_dns_record('txtrecord', idnsname, record)

    def add_ptr_record(self, idnsname, record, dns_zone, ttl=_DEFAULT_TTL):
        """Add PTR record."""
        return self.add_dns_record(
            'ptrrecord', idnsname, record, dns_zone=dns_zone, ttl=ttl
        )

    def delete_ptr_record(self, idnsname, record, dns_zone):
        """Delete PTR record."""
        return self.delete_dns_record(
            'ptrrecord', idnsname, record, dns_zone=dns_zone
        )

    def add_user(self, user_name, first_name, last_name, user_type):
        """Add new user to IPA server."""
        args = [user_name]
        options = {
            'givenname': first_name,
            'sn': last_name,
            'userclass': user_type,
        }
        return self._call('user_add', args, options)['result']

    def delete_user(self, user_name):
        """Delete user from IPA server."""
        args = [user_name]
        return self._call('user_del', args)['result']

    def list_users(self, pattern=None):
        """Retrieve user records from IPA server."""
        args = [pattern] if pattern else []
        options = {'sizelimit': 0}
        return self._call('user_find', args, options)['result']

    def get_user(self, user_name):
        """Show details about IPA user."""
        args = [user_name]
        return self._call('user_show', args)['result']
