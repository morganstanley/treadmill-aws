"""
Unit test for EC2 node.
"""

import unittest
import mock

from treadmill_aws.infra.setup.node import Node


class NodeTest(unittest.TestCase):
    """Tests EC2 Node"""

    @mock.patch('treadmill_aws.infra.instances.Instances')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_hostnames_for_multiple(self, _conn_mock, instance_mock):
        """Test hostnames for multiple."""
        instance_mock.get_hostnames_by_roles = mock.Mock(return_value={
            'IPA': 'ipa-hostname',
            'LDAP': 'ldap-hostname',
        })

        node = Node(
            vpc_id='vpc-id',
            name='node'
        )
        _ldap_hostname, _ipa_hostname = node.hostnames_for(
            roles=['LDAP', 'IPA']
        )

        self.assertEqual(_ldap_hostname, 'ldap-hostname')
        self.assertEqual(_ipa_hostname, 'ipa-hostname')

    @mock.patch('treadmill_aws.infra.instances.Instances')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_hostnames_for_single(self, _conn_mock, instance_mock):
        """Test hostnames for single."""
        instance_mock.get_hostnames_by_roles = mock.Mock(return_value={
            'IPA': 'ipa-hostname',
        })

        node = Node(
            vpc_id='vpc-id',
            name='node'
        )
        _ipa_hostname, = node.hostnames_for(
            roles=['IPA']
        )

        self.assertEqual(_ipa_hostname, 'ipa-hostname')

    @mock.patch('treadmill_aws.infra.instances.Instances')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_hostnames_for_none(self, _conn_mock, instance_mock):
        """Test hostnames for none."""
        instance_mock.get_hostnames_by_roles = mock.Mock(return_value={})

        node = Node(
            vpc_id='vpc-id',
            name='node'
        )

        self.assertEqual(node.hostnames_for(roles=['IPA']), [None])
        self.assertEqual(node.hostnames_for(roles=[]), [])

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_zk_url_cluster(self, _conn_mock):
        """Tst zk url cluster."""
        node = Node(
            vpc_id='vpc-id',
            name='node'
        )

        # pylint: disable=protected-access
        _zk_url = node._zk_url(
            hostname='zk1,zk2,zk3'
        )

        self.assertEqual(_zk_url, 'zookeeper://foo@zk1:2181,zk2:2181,zk3:2181')

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_zk_url_standalone(self, _conn_mock):
        """Test zk url standalone."""
        node = Node(
            vpc_id='vpc-id',
            name='node'
        )

        # pylint: disable=protected-access
        _zk_url = node._zk_url(
            hostname='zk1'
        )

        self.assertEqual(_zk_url, 'zookeeper://foo@zk1:2181')

    @mock.patch('treadmill_aws.infra.instances.Instances')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    @mock.patch('treadmill_aws.infra.vpc.VPC')
    def test_destroy_by_instance_id(self, _vpc_mock,
                                    _conn_mock, instance_mock):
        """Test destory by instance id."""
        _instances_obj_mock = mock.Mock()
        instance_mock.get = mock.Mock(return_value=_instances_obj_mock)
        instance_mock.get_hostnames_by_roles = mock.Mock(return_value={
            'NODE': 'node1-1000.domain'
        })

        node = Node(
            vpc_id='vpc-id',
            name='node'
        )
        node.destroy(
            instance_id='instance-id'
        )

        instance_mock.get.assert_called_once_with(ids=['instance-id'])
        _instances_obj_mock.terminate.assert_called_once_with()

    @mock.patch('treadmill_aws.infra.instances.Instances')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    @mock.patch('treadmill_aws.infra.vpc.VPC')
    def test_destroy_by_instance_name(self, _vpc_mock,
                                      _conn_mock, instance_mock):
        """Test destroy by instance name."""
        _instances_obj_mock = mock.Mock()
        instance_mock.get = mock.Mock(return_value=_instances_obj_mock)
        instance_mock.get_hostnames_by_roles = mock.Mock(return_value={
            'NODE': 'node-instance-name.domain'
        })

        node = Node(
            vpc_id='vpc-id',
            name='node-instance-name'
        )
        node.destroy()

        instance_mock.get.assert_called_once_with(
            filters=[
                {
                    'Name': 'tag-key',
                    'Values': ['Name']
                },
                {
                    'Name': 'tag-value',
                    'Values': ['node-instance-name']
                },
            ]
        )
        _instances_obj_mock.terminate.assert_called_once_with()

    @mock.patch('treadmill_aws.infra.instances.Instances')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    @mock.patch('treadmill_aws.infra.vpc.VPC')
    def test_destroy_without_identifier(self, _vpc_mock, _conn_mock,
                                        instance_mock):
        """Test destroy without identifier."""
        instance_mock.get = mock.Mock()

        node = Node(
            vpc_id='vpc-id',
            name=None
        )
        node.destroy()

        instance_mock.get.assert_not_called()
