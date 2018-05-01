""" DNS Daemon tests """
# Suppress pylint warnings concerning access to protected members
# pylint: disable=W0212
# Suppress pylint warnings concerning imports of mocked classes
# pylint: disable=W0611

import os
import unittest

import mock

import treadmill
import treadmill_aws
from treadmill_aws import dnsmonitor
from treadmill_aws import ipaclient


class DNSMonitorHelperTests(unittest.TestCase):
    """Test DNSDaemon helper functions.
    """

    @mock.patch('treadmill_aws.ipaclient')
    def test_find_app_dns(self, mock_ipaclient):
        """Test that idnsname is rendered correctly.
        """

        mock_ipaclient.domain = 'foo.com'

        dnsmonitor.find_app_dns(
            ipaclient=mock_ipaclient,
            server='ssh',
            protocol='tcp',
            app_name='fooapi')

        mock_ipaclient.get_ipa_dns.assert_called_with(
            idnsname='_ssh._tcp.fooapi.foo.com')

    def test_generate_srv_record(self):
        """Test that SRV records are rendered correctly.
        """

        result = dnsmonitor.generate_srv_record(
            cell_name='subnet-123',
            server='ssh',
            protocol='tcp',
            app_name='fooapi',
            endpoints=[('host1.foo.com', 5000)])

        assert result == {'idnsname': '_ssh._tcp.fooapi.subnet-123',
                          'record': '10 10 5000 host1.foo.com.',
                          'type': 'srvrecord'}

    def test_get_filesystem_context(self):
        """Test that script parses ZK endpoint path correctly.
        """

        result = dnsmonitor.get_filesystem_context(
            endpoint_dir='/tmp/foo/endpoints',
            path='/tmp/foo/endpoints/proid/appname#001:tcp:ssh')

        assert result == {'app': 'appname',
                          'file_name': 'appname#001:tcp:ssh',
                          'proid_dir': '/tmp/foo/endpoints/proid',
                          'protocol': 'tcp',
                          'server': 'ssh'}

    def test_zk_target_from_file(self):
        """Test that script parses ZK endpoint file on disk correctly.
        """

        with mock.patch("builtins.open",
                        mock.mock_open(
                            read_data='host1.foo.com:5000')) as mock_file:

            result = dnsmonitor.get_zk_target_from_file('/foo')

        assert result == ('host1.foo.com', 5000)

    @mock.patch('treadmill_aws.ipaclient')
    def test_mirror_zookeeper(self, mock_ipaclient):
        """Test mirror_zookeeper operations:
           - Comparison of equal ZK and IPA records - no changes
           - New ZK records - Add ZK records to IPA
           - Removed ZK records - Remove ZK records from IPA
        """

        sample_dns_records = [
            {'dn': 'idnsname=_http._tcp.testapi1.subnet-123,'
                   'idnsname=foo.com.,cn=dns,dc=foo,dc=com',
             'idnsname': '_http._tcp.testapi1.subnet-123',
             'record': '10 10 1234 host1.foo.com.',
             'type': 'srvrecord'}]

        # Case 1- equal ZK and IPA record sets.
        dnsmonitor.filter_raw_records = mock.MagicMock(
            return_value=sample_dns_records)

        dnsmonitor.mirror_zookeeper(cell_name='subnet123',
                                    ipaclient=mock_ipaclient,
                                    zk_records=sample_dns_records)

        assert mock_ipaclient.add_ipa_dns.call_count == 0
        assert mock_ipaclient.del_ipa_dns.call_count == 0

        mock_ipaclient.reset_mock()

        # Case 2- New ZK record, missing in IPA
        dnsmonitor.filter_raw_records = mock.MagicMock(
            return_value=[])

        dnsmonitor.mirror_zookeeper(cell_name='subnet123',
                                    ipaclient=mock_ipaclient,
                                    zk_records=sample_dns_records)

        assert mock_ipaclient.add_ipa_dns.call_count == 1
        assert mock_ipaclient.del_ipa_dns.call_count == 0

        mock_ipaclient.reset_mock()

        # Case 3- ZK record deleted, present in IPA
        dnsmonitor.filter_raw_records = mock.MagicMock(
            return_value=sample_dns_records)

        dnsmonitor.mirror_zookeeper(cell_name='subnet123',
                                    ipaclient=mock_ipaclient,
                                    zk_records=[])

        assert mock_ipaclient.add_ipa_dns.call_count == 0
        assert mock_ipaclient.del_ipa_dns.call_count == 1


class DNSMonitorTests(unittest.TestCase):
    """ Tests DNSMonitor interface """

    @mock.patch('treadmill_aws.ipaclient')
    def test_on_created(self, mock_ipaclient):
        """Test end-to-end creation of IPA records.
        """
        client = dnsmonitor.DNSMonitor(cell_name='subnet123',
                                       ipaclient=mock_ipaclient,
                                       zkfs_dir='/foo')

        # Populate the get_zk_target_from_file:
        with mock.patch("builtins.open",
                        mock.mock_open(
                            read_data='host1.foo.com:5000')) as mock_file:

            client._on_created('/foo/endpoints/proid/appname#001:tcp:ssh')

        mock_ipaclient.add_ipa_dns.assert_called_with(
            record_name='_ssh._tcp.appname.subnet123',
            record_type='srvrecord',
            record_value='10 10 5000 host1.foo.com.')

    @mock.patch('treadmill_aws.ipaclient')
    def test_on_deleted(self, mock_ipaclient):
        """Test that client.sync() gets called when _on_deleted is called.
        """
        client = dnsmonitor.DNSMonitor(cell_name='subnet123',
                                       ipaclient=mock_ipaclient,
                                       zkfs_dir='/foo')
        client.sync = mock.MagicMock()
        client._on_deleted('/foo')

        assert client.sync.call_count == 1

    @mock.patch('treadmill_aws.ipaclient')
    def test_sync(self, mock_ipaclient):
        """Test ZK record generation operations.
        """
        client = dnsmonitor.DNSMonitor(cell_name='subnet123',
                                       ipaclient=mock_ipaclient,
                                       zkfs_dir='/foo')

        dnsmonitor.mirror_zookeeper = mock.MagicMock()

        with mock.patch('os.listdir') as mocked_listdir:
            # Populate the get_zk_target_from_file:
            with mock.patch("builtins.open",
                            mock.mock_open(
                                read_data='host1.foo.com:5000')) as mock_file:

                # Mock directory with one file target:
                mocked_listdir.return_value = ['appname#001:tcp:ssh']

                client.sync()

                dnsmonitor.mirror_zookeeper.assert_called_with(
                    cell_name='subnet123',
                    ipaclient=mock_ipaclient,
                    zk_records=[{'idnsname': '_ssh._tcp.appname.subnet123',
                                 'record': '10 10 5000 host1.foo.com.',
                                 'type': 'srvrecord'}])

                # Mock directory with no targets:
                mocked_listdir.return_value = []

                client.sync()

                dnsmonitor.mirror_zookeeper.assert_called_with(
                    cell_name='subnet123',
                    ipaclient=mock_ipaclient,
                    zk_records=[])


if __name__ == '__main__':
    unittest.main()
