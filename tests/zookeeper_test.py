"""Unit test for zookeeper plugin.
"""

import unittest

import mock
import pkg_resources

from treadmill_aws.plugins import zookeeper as zksasl


@unittest.skipUnless('sasl' in pkg_resources.get_distribution('kazoo').extras,
                     'Kazoo does not have SASL support')
class ZookeeperTest(unittest.TestCase):
    """Tests Zookeeper plugin.
    """
    @mock.patch('treadmill.zkutils.ZkClient.__init__')
    def test_connect_without_connargs(self, zkclient_mock):
        """Test connect.
        """
        zk = zksasl.SASLZkClient(
            hosts='zkservice@123:21'
        )

        zkclient_mock.assert_called_once_with(
            hosts='123:21',
            sasl_data={
                'service': 'zkservice',
                'mechanisms': ['GSSAPI']
            }
        )

    @mock.patch('treadmill.zkutils.ZkClient.__init__')
    def test_connect_with_connargs(self, zkclient_mock):
        """Test connect with args.
        """
        zk = zksasl.SASLZkClient(
            hosts='lala@foobar:123',
            sasl_data={
                'service': 'foo',
                'mechanisms': ['bar']
            }
        )

        zkclient_mock.assert_called_once_with(
            hosts='foobar:123',
            sasl_data={
                'service': 'lala',
                'mechanisms': ['bar']
            }
        )

    @mock.patch('kazoo.security.make_acl')
    def test_make_user_acl(self, make_acl_mock):
        """Test constucting user acl."""
        zk = zksasl.SASLZkClient()
        zk.make_user_acl('foo', 'rw')

        make_acl_mock.assert_called_once_with(
            scheme='sasl', credential='foo', read=True,
            write=True, create=False, delete=False, admin=False
        )

    @mock.patch('kazoo.security.make_acl')
    def test_make_role_acl(self, make_acl_mock):
        """Test constructing role acl for valid role."""
        zk = zksasl.SASLZkClient()
        zk.make_role_acl('servers', 'ra')

        make_acl_mock.assert_called_once_with(
            scheme='sasl', credential='file:///treadmill/roles/servers',
            read=True, write=False, delete=False, create=False, admin=True
        )

    @mock.patch('kazoo.security.make_acl')
    @mock.patch('treadmill.syscall.krb5.get_host_realm',
                mock.Mock(return_value=['my-realm']))
    def test_make_host_acl(self, make_acl_mock):
        """Test host acl."""
        zk = zksasl.SASLZkClient()
        zk.make_host_acl('foo', 'rdwca')

        make_acl_mock.assert_called_once_with(
            scheme='sasl', credential='host/foo@my-realm', read=True,
            write=True, delete=True, create=True, admin=True
        )


if __name__ == '__main__':
    unittest.main()
