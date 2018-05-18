""" Test ipaclient functions
"""
import unittest

import dns.resolver
import mock

from treadmill_aws import ipaclient


# Suppress pylint warnings concerning access to protected member _post
# pylint: disable=W0212
# Suppress pylint warnings concerning imports of mocked classes
# pylint: disable=W0611
class IPAHelperTests(unittest.TestCase):
    """Test IPAClient helper functions.
    """

    class FakeIPAResponse(object):
        """Fake IPA JSON-RPC response object.
        """
        text = ''
        _json = {}

        def json(self=None):
            """Fake JSON response.
            """
            return self._json

    fake_multi_records = {'error': None,
                          'id': 0,
                          'principal': 'admin@FOO.COM',
                          'result': {
                              'count': 3,
                              'result': [
                                  {'dn': 'idnsname=_http._tcp.testapi.'
                                         'subnet-123,idnsname=foo.com.,'
                                         'cn=dns,dc=foo,dc=com',
                                   'idnsname': [
                                       '_http._tcp.testapi.subnet-123'],
                                   'srvrecord': ['10 10 1234 host1.foo.com.']},
                                  {'dn': 'idnsname=_http._tcp.testapi2.'
                                         'subnet-123,idnsname=foo.com.,'
                                         'cn=dns,dc=foo,dc=com',
                                   'idnsname': [
                                       '_http._tcp.testapi2.subnet-123'],
                                   'srvrecord': ['10 10 1234 host2.foo.com.']},
                                  {'dn': 'idnsname=_http._tcp.testapi3.'
                                         'subnet-456,idnsname=foo.com.,'
                                         'cn=dns,dc=foo,dc=com',
                                   'idnsname': [
                                       '_http._tcp.testapi3.subnet-456'],
                                   'srvrecord': ['10 10 1234 host3.foo.com.']},
                                  {'arecord': ['192.168.0.2'],
                                   'dn': 'idnsName=host4,idnsname='
                                         'foo.com.,cn=dns,dc=foo,dc=com',
                                   'idnsname': ['host4'],
                                   'sshfprecord': ['1 1 ABC',
                                                   '1 2 ABC 3E180D08',
                                                   '3 1 ABC',
                                                   '3 2 ABC 22FC10E0',
                                                   '4 1 ABC',
                                                   '4 2 ABC 4DDA73C1']}],
                              'summary': None,
                              'truncated': False},
                          'version': '4.5.0'}

    no_records = {'error': None,
                  'id': 0,
                  'principal': 'admin@FOO.COM',
                  'result': {'count': 0,
                             'result': [],
                             'summary': None,
                             'truncated': False},
                  'version': '4.5.0'}

    truncated_records = {'error': None,
                         'id': 0,
                         'principal': 'admin@FOO.COM',
                         'result': {'count': 0,
                                    'result': [],
                                    'summary': None,
                                    'truncated': True},
                         'version': '4.5.0'}

    def test_get_ipa_server_from_dns(self):
        """Test IPA server resolution from DNS.
        """

        class FakeDNSResponse(object):
            """Fake dns.resolver.query object.
            """

            def __init__(self, host):
                """ Assign argument as self.host """
                self.host = host

            def to_text(self):
                """ Return self.host when to_text() called """
                return '0 100 88 {}.'.format(self.host)

        # Test single DNS response
        dns.resolver.query = mock.MagicMock(
            return_value=[FakeDNSResponse('ipa1.foo.com')])

        result = ipaclient.get_ipa_server_from_dns('foo.com')
        assert result == 'ipa1.foo.com.'

        # Test multiple DNS responses
        dns.resolver.query = mock.MagicMock(
            return_value=[FakeDNSResponse('ipa1.foo.com'),
                          FakeDNSResponse('ipa2.foo.com')])

        result = ipaclient.get_ipa_server_from_dns('foo.com')
        assert result in ['ipa1.foo.com.', 'ipa2.foo.com.']

        # Test no DNS response
        dns.resolver.query = mock.MagicMock(
            return_value=[])

        with self.assertRaises(Exception) as context:
            result = ipaclient.get_ipa_server_from_dns('foo.com')
            self.assertTrue('No IPA Servers Found' in context.exception)

    def test_filter_raw_records(self):
        """Test formatting and filtering JSON IPA record output.
           Filters are based on cell name and record type.
        """

        # Test single SRV record returned
        result = ipaclient.filter_raw_records(
            cell_name='subnet-456',
            raw_records=self.fake_multi_records,
            record_type='srvrecord')

        assert result == [
            {'dn': 'idnsname=_http._tcp.testapi3.subnet-456,'
                   'idnsname=foo.com.,cn=dns,dc=foo,dc=com',
             'idnsname': '_http._tcp.testapi3.subnet-456',
             'record': '10 10 1234 host3.foo.com.',
             'type': 'srvrecord'}]

        # Test multiple SRV records returned
        result = ipaclient.filter_raw_records(
            cell_name='subnet-123',
            raw_records=self.fake_multi_records,
            record_type='srvrecord')

        assert result == [
            {'dn': 'idnsname=_http._tcp.testapi.subnet-123,'
                   'idnsname=foo.com.,cn=dns,dc=foo,dc=com',
             'idnsname': '_http._tcp.testapi.subnet-123',
             'record': '10 10 1234 host1.foo.com.',
             'type': 'srvrecord'},
            {'dn': 'idnsname=_http._tcp.testapi2.subnet-123,'
                   'idnsname=foo.com.,cn=dns,dc=foo,dc=com',
             'idnsname': '_http._tcp.testapi2.subnet-123',
             'record': '10 10 1234 host2.foo.com.',
             'type': 'srvrecord'}]

        # Test no records returned
        result = ipaclient.filter_raw_records(cell_name='subnet-123',
                                              raw_records=self.no_records,
                                              record_type='srvrecord')
        assert result == []

    def test_check_response(self):
        """Test error handling of JSON IPA record output.
        """

        # Test truncated result handling
        truncated_response = self.FakeIPAResponse()
        truncated_response._json = self.truncated_records

        with self.assertRaises(ipaclient.IPAError):
            ipaclient.check_response(truncated_response)


class IPAClientTest(unittest.TestCase):
    """Tests IPA client interface.
    """

    class FakeResponse(object):
        """Fake IPA response object.
        """

        def json(self=None):
            """Fake JSON response.
            """

            return {'error': None,
                    'result':
                    {'result': [
                        {'krbprincipalname': [
                            'host/host.foo.com@FOO.COM'],
                         'dn': 'fqdn=host.foo.com,dc=foo,dc=com',
                         'fqdn': ['host.foo.com'],
                         'sshpubkeyfp': [
                             'SHA256:ZEQFEjXYEqYhtk (ssh-rsa)',
                             'SHA256:W9J6SunkvJU (ecdsa-sha2-nistp256)',
                             'SHA256:sT7bx2Agf6Mx0 (ssh-ed25519)'],
                         'krbcanonicalname': [
                             'host/host.foo.com@FOO.COM']}],
                     'count': 1,
                     'truncated': False,
                     'summary': '1 hosts matched'},
                    'id': 0,
                    'version': '4.5.0',
                    'principal': 'admin@FOO.COM'}

    def setUp(self):
        ipaclient.get_ipa_server_from_dns = mock.MagicMock(
            return_value='ipa1.foo.com.')
        self.test_client = ipaclient.IPAClient(certs='/foo', domain='foo.com')
        self.test_client._post = mock.MagicMock()

    def test_enroll_host_payload(self):
        """Test that enroll_ipa_host formats payload correctly.
        """
        self.test_client.enroll_host(hostname='host.foo.com')
        self.test_client._post.assert_called_with(
            payload={'method': 'host_add',
                     'id': 0, 'params': [['host.foo.com'],
                                         {'random': True,
                                          'version': '2.28',
                                          'force': True}]})

    def test_unenroll_host_payload(self):
        """Test that unenroll_ipa_host formats payload correctly.
        """
        self.test_client.unenroll_host(hostname='host.foo.com')
        self.test_client._post.assert_called_with(
            payload={'id': 0,
                     'params': [
                         ['host.foo.com'],
                         {'updatedns': True,
                          'version': '2.28'}],
                     'method': 'host_del'})

    def test_get_hosts_results(self):
        """Test that get_ipa_hosts parses IPA output correctly.
        """
        self.test_client._post = mock.MagicMock(return_value=self.FakeResponse)
        results = self.test_client.get_hosts()
        assert results == ['host.foo.com']

    def test_add_dns_record_payload(self):
        """Test that add_ipa_dns formats payload correctly.
        """
        self.test_client.add_dns_record(record_type='srvrecord',
                                        record_name='_tcp._ssh.cellname',
                                        record_value='10 10 10 host.foo.com')
        self.test_client._post.assert_called_with(
            payload={'method': 'dnsrecord_add',
                     'params': [['foo.com', '_tcp._ssh.cellname'],
                                {'srvrecord': '10 10 10 host.foo.com',
                                 'version': '2.28'}],
                     'id': 0})

    def test_delete_dns_record_payload(self):
        """Test that del_dns_record formats payload correctly.
        """
        self.test_client.delete_dns_record(
            record_type='srvrecord',
            record_name='_tcp._ssh.cellname',
            record_value='10 10 10 host.foo.com')
        self.test_client._post.assert_called_with(
            payload={'method': 'dnsrecord_del',
                     'params': [['foo.com', '_tcp._ssh.cellname'],
                                {'srvrecord': '10 10 10 host.foo.com',
                                 'version': '2.28'}],
                     'id': 0})

    def test_get_dns_record_payload(self):
        """Test that get_dns_record formats payload correctly.
        """
        # With idnsname
        self.test_client.get_dns_record(idnsname='_tcp._ssh.cellname')
        self.test_client._post.assert_called_with(
            payload={'id': 0,
                     'method': 'dnsrecord_find',
                     'params': [['foo.com', '_tcp._ssh.cellname'],
                                {'version': '2.28',
                                 'sizelimit': 0}]})
        # Without idnsname
        self.test_client.get_dns_record()
        self.test_client._post.assert_called_with(
            payload={'id': 0,
                     'method': 'dnsrecord_find',
                     'params': [['foo.com'],
                                {'version': '2.28',
                                 'sizelimit': 0}]})

    def test_add_user(self):
        """ Test that add_user formats payload correctly """

        self.test_client.add_user(user_name='user1',
                                  first_name='foo',
                                  last_name='proid',
                                  user_type='proid')

        self.test_client._post.assert_called_with(
            payload={'method': 'user_add',
                     'params': [['user1'],
                                {'givenname': 'foo',
                                 'sn': 'proid',
                                 'userclass': 'proid',
                                 'version': '2.28'}],
                     'id': 0})

    def test_delete_user(self):
        """ Test that del_user formats payload correctly """

        self.test_client.delete_user(user_name='user1')

        self.test_client._post.assert_called_with(
            payload={'method': 'user_del',
                     'params': [['user1'],
                                {'version': '2.28'}],
                     'id': 0})

    def test_list_users(self):
        """ Test that get_user formats payload correctly """
        # With pattern
        self.test_client.list_users(pattern='foo')
        self.test_client._post.assert_called_with(
            payload={'id': 0,
                     'method': 'user_find',
                     'params': [['foo'],
                                {'version': '2.28',
                                 'sizelimit': 0}]})

        # Without pattern
        self.test_client.list_users()
        self.test_client._post.assert_called_with(
            payload={'id': 0,
                     'method': 'user_find',
                     'params': [[],
                                {'version': '2.28',
                                 'sizelimit': 0}]})

    def test_show_user(self):
        """ Test that show_user formats payload correctly """
        self.test_client.show_user(user_name='foo')
        self.test_client._post.assert_called_with(
            payload={'id': 0,
                     'method': 'user_show',
                     'params': [['foo'],
                                {'version': '2.28'}]})


if __name__ == '__main__':
    unittest.main()
