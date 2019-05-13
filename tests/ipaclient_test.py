""" Test ipaclient functions
"""
import unittest

import mock

from treadmill_aws import ipaclient


# Suppress pylint warnings concerning access to protected member _post
# pylint: disable=W0212
# Suppress pylint warnings concerning imports of mocked classes
# pylint: disable=W0611
class IPAHelperTests(unittest.TestCase):
    """Test IPAClient helper functions.
    """

    class FakeIPAResponse:
        """Fake IPA JSON-RPC response object.
        """
        text = ''
        status_code = 200
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

    @mock.patch('treadmill.dnsutils.srv')
    def test_get_ipa_urls_from_dns(self, srv_mock):
        """Test getting IPA servers from DNS.
        """
        srv_mock.return_value = [
            ('ipa1.foo.com', 88, 0, 80),
            ('ipa2.foo.com', 88, 1, 60),
            ('ipa3.foo.com', 88, 1, 40),
        ]

        ipa_urls = ipaclient.get_ipa_urls_from_dns('foo.com')

        self.assertEqual(
            ipa_urls,
            [
                'https://ipa1.foo.com/ipa',
                'https://ipa2.foo.com/ipa',
                'https://ipa3.foo.com/ipa',
            ]
        )

        # Test no DNS response.
        srv_mock.return_value = []

        with self.assertRaisesRegex(Exception, 'No IPA servers found'):
            ipaclient.get_ipa_urls_from_dns('foo.com')

    def test_check_response(self):
        """Test error handling of JSON IPA record output.
        """

        # Test truncated result handling
        truncated_response = self.FakeIPAResponse()
        truncated_response._json = self.truncated_records

        with self.assertRaises(ipaclient.IPAError):
            ipaclient.check_response(truncated_response)


class IPAClientTest(unittest.TestCase):
    """Test IPAClient interface.
    """

    def setUp(self):
        self.get_ipa_urls_patcher = mock.patch(
            'treadmill_aws.ipaclient.get_ipa_urls_from_dns'
        )
        get_ipa_urls_mock = self.get_ipa_urls_patcher.start()
        get_ipa_urls_mock.return_value = ['https://ipa1.foo.com/ipa']

        self.test_client = ipaclient.IPAClient(certs='/foo', domain='foo.com')
        self.test_client._post = mock.MagicMock()

    def tearDown(self):
        self.get_ipa_urls_patcher.stop()

    def test_enroll_host_payload(self):
        """Test that enroll_ipa_host formats payload correctly.
        """
        self.test_client.enroll_host(hostname='host.foo.com')
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'method': 'host_add',
             'id': 0, 'params': [['host.foo.com'],
                                 {'random': True,
                                  'version': '2.28',
                                  'force': True}]}
        )

    def test_unenroll_host_payload(self):
        """Test that unenroll_ipa_host formats payload correctly.
        """
        self.test_client.unenroll_host(hostname='host.foo.com')
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'id': 0,
             'params': [
                 ['host.foo.com'],
                 {'updatedns': True,
                  'version': '2.28'}],
             'method': 'host_del'}
        )

    def test_list_hosts_results(self):
        """Test that list_hosts parses IPA output correctly.
        """
        self.test_client._post = mock.MagicMock(
            return_value={'result': [{'fqdn': ['host.foo.com']}]}
        )
        results = self.test_client.list_hosts()
        assert results == ['host.foo.com']

    def test_add_dns_record_payload(self):
        """Test that add_ipa_dns formats payload correctly.
        """
        self.test_client.add_dns_record(
            'srvrecord', '_tcp._ssh.cellname', '10 10 10 host.foo.com'
        )
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'method': 'dnsrecord_add',
             'params': [['foo.com', '_tcp._ssh.cellname'],
                        {'srvrecord': '10 10 10 host.foo.com',
                         'dnsttl': 5,
                         'version': '2.28'}],
             'id': 0}
        )

    def test_delete_dns_record_payload(self):
        """Test that del_dns_record formats payload correctly.
        """
        self.test_client.delete_dns_record(
            'srvrecord', '_tcp._ssh.cellname', '10 10 10 host.foo.com'
        )
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'method': 'dnsrecord_del',
             'params': [['foo.com', '_tcp._ssh.cellname'],
                        {'srvrecord': '10 10 10 host.foo.com',
                         'version': '2.28'}],
             'id': 0}
        )

    def test_get_dns_record_payload(self):
        """Test that get_dns_record formats payload correctly.
        """
        self.test_client.get_dns_record('_tcp._ssh.cellname')
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'id': 0,
             'method': 'dnsrecord_show',
             'params': [['foo.com', '_tcp._ssh.cellname'],
                        {'version': '2.28'}]}
        )

    def test_list_dns_records_payload(self):
        """Test that list_dns_records formats payload correctly.
        """
        self.test_client.list_dns_records()
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'id': 0,
             'method': 'dnsrecord_find',
             'params': [['foo.com'],
                        {'version': '2.28',
                         'sizelimit': 0}]}
        )

    def test_add_user(self):
        """ Test that add_user formats payload correctly """
        self.test_client.add_user('user1', 'foo', 'proid', 'proid')
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'method': 'user_add',
             'params': [['user1'],
                        {'givenname': 'foo',
                         'sn': 'proid',
                         'userclass': 'proid',
                         'version': '2.28'}],
             'id': 0}
        )

    def test_delete_user(self):
        """ Test that del_user formats payload correctly """
        self.test_client.delete_user('user1')
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'method': 'user_del',
             'params': [['user1'],
                        {'version': '2.28'}],
             'id': 0}
        )

    def test_list_users(self):
        """ Test that get_user formats payload correctly """
        # With pattern
        self.test_client.list_users(pattern='foo')
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'id': 0,
             'method': 'user_find',
             'params': [['foo'],
                        {'version': '2.28',
                         'sizelimit': 0}]}
        )

        # Without pattern
        self.test_client.list_users()
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'id': 0,
             'method': 'user_find',
             'params': [[],
                        {'version': '2.28',
                         'sizelimit': 0}]}
        )

    def test_show_user(self):
        """ Test that show_user formats payload correctly """
        self.test_client.get_user('foo')
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'id': 0,
             'method': 'user_show',
             'params': [['foo'],
                        {'version': '2.28'}]}
        )

    def test_hostgroup_add_member(self):
        """ Test that hostgroup_add_member formats payload correctly """
        self.test_client.hostgroup_add_member('foo', 'foo.com')
        self.test_client._post.assert_called_with(
            mock.ANY,
            {'id': 0,
             'method': 'hostgroup_add_member',
             'params': [['foo'],
                        {'host': 'foo.com',
                         'version': '2.28'}]}
        )


if __name__ == '__main__':
    unittest.main()
