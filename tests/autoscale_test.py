"""Tests for autoscale."""

import unittest

import mock
from botocore import exceptions as botoexc

from treadmill import context

from treadmill_aws import autoscale
from treadmill_aws import awscontext


def _mock_cell(admin_mock, stateapi_mock,
               partitions, servers, servers_state, apps_state):
    admin_cell_mock = admin_mock.cell.return_value
    admin_srv_mock = admin_mock.server.return_value

    admin_cell_mock.get.return_value = {
        'partitions': partitions,
    }
    admin_srv_mock.list.return_value = servers

    apps_columns = ['instance', 'partition', 'server']
    servers_columns = ['name', 'state', 'cpu', 'mem', 'disk']

    stateapi_mock.return_value = (
        {'columns': apps_columns, 'data': apps_state},
        {'columns': servers_columns, 'data': servers_state},
    )


def _raise_if(check, err):
    if check:
        raise err


@mock.patch('treadmill.context.GLOBAL.zk', mock.Mock())
class AutoscaleTest(unittest.TestCase):
    """Test autoscale."""

    def setUp(self):
        context.GLOBAL.cell = 'test'
        context.GLOBAL.ldap_suffix = 'dc=test'
        context.GLOBAL.dns_domain = 'foo.com'
        awscontext.GLOBAL.ipa_domain = 'foo.com'

    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale._query_stateapi')
    @mock.patch('treadmill.context.Context.admin')
    def test_scale_up_no_idle(self, admin_mock, stateapi_mock):
        """Test scaling up with no idle servers present."""

        mock_zkclient = context.GLOBAL.zk.conn
        mock_zkclient.get_children.return_value = []

        # Ratio: 0.5
        # Pending apps: 3, no servers - create 2 servers.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 1, 'max_servers': 9}}},
            ],
            servers=[],
            servers_state=[],
            apps_state=[
                ('proid.app#001', 'partition', None),
                ('proid.app#002', 'partition', None),
                ('proid.app#003', 'partition', None),
            ],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_called_once_with(
            2, 'partition', pool=None
        )
        autoscale.delete_servers_by_name.assert_not_called()

        autoscale.create_n_servers.reset_mock()
        autoscale.delete_servers_by_name.reset_mock()

        # Ratio: 0.5
        # Pending apps: 100, no servers, max servers: 9 - create 9 severs.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 1, 'max_servers': 9}}},
            ],
            servers=[],
            servers_state=[],
            apps_state=[
                ('proid.app#%03d' % i, 'partition', None) for i in range(100)
            ],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_called_once_with(
            9, 'partition', pool=None
        )
        autoscale.delete_servers_by_name.assert_not_called()

        autoscale.create_n_servers.reset_mock()
        autoscale.delete_servers_by_name.reset_mock()

        # Ratio: 1.0 (down and frozen servers excluded).
        # Pending apps: 3, no idle servers - create 3 servers.
        # Down and frozen servers have apps placed on them - don't delete.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 1, 'max_servers': 9}}},
            ],
            servers=[
                {'_id': 'server1', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server2', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server3', 'partition': 'partition',
                 '_create_timestamp': 100.0},
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
                ('server2', 'down', 100, 100, 100),
                ('server3', 'frozen', 100, 100, 100),
            ],
            apps_state=[
                ('proid.app#001', 'partition', 'server1'),
                ('proid.app#002', 'partition', 'server2'),
                ('proid.app#003', 'partition', 'server3'),
                ('proid.app#004', 'partition', 'server3'),
                ('proid.app#005', 'partition', 'server3'),
                ('proid.app#006', 'partition', 'server3'),
                ('proid.app#007', 'partition', None),
                ('proid.app#008', 'partition', None),
                ('proid.app#009', 'partition', None),
            ],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_called_once_with(
            3, 'partition', pool=None
        )
        autoscale.delete_servers_by_name.assert_not_called()

    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale._query_stateapi')
    @mock.patch('treadmill.context.Context.admin')
    @mock.patch('time.time', mock.Mock(return_value=1000.0))
    def test_scale_up_with_idle(self, admin_mock, stateapi_mock):
        """Test scaling up with some idle servers present."""

        mock_zkclient = context.GLOBAL.zk.conn
        mock_zkclient.get_children.return_value = []

        # Ratio: 0.5
        # Pending apps: 1, idle servers: 1 - don't create anything.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 1, 'max_servers': 9}}},
            ],
            servers=[
                {'_id': 'server1', 'partition': 'partition',
                 '_create_timestamp': 100.0},
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
            ],
            apps_state=[
                ('proid.app#001', 'partition', None),
            ],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_not_called()
        autoscale.delete_servers_by_name.assert_not_called()

        autoscale.create_n_servers.reset_mock()
        autoscale.delete_servers_by_name.reset_mock()

        # Ratio: 0.5
        # Pending apps: 3, idle servers: 2 - don't create anything.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 1, 'max_servers': 9}}},
            ],
            servers=[
                {'_id': 'server1', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server2', 'partition': 'partition',
                 '_create_timestamp': 100.0},
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
                ('server2', 'up', 100, 100, 100),
            ],
            apps_state=[
                ('proid.app#001', 'partition', None),
                ('proid.app#002', 'partition', None),
                ('proid.app#003', 'partition', None),
            ],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_not_called()
        autoscale.delete_servers_by_name.assert_not_called()

        autoscale.create_n_servers.reset_mock()
        autoscale.delete_servers_by_name.reset_mock()

        # Ratio: 1.0.
        # Pending apps: 3, idle servers: 2 - create 1 server.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 1, 'max_servers': 9}}},
            ],
            servers=[
                {'_id': 'server1', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server2', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server3', 'partition': 'partition',
                 '_create_timestamp': 999.0},
                {'_id': 'server4', 'partition': 'partition',
                 '_create_timestamp': 100.0},
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
                ('server2', 'up', 100, 100, 100),
                ('server3', 'down', None, None, None),  # Didn't report - new.
                ('server4', 'down', None, None, None),  # Didn't report - down.
            ],
            apps_state=[
                ('proid.app#001', 'partition', 'server1'),
                ('proid.app#002', 'partition', None),
                ('proid.app#003', 'partition', None),
                ('proid.app#004', 'partition', None),
            ],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_called_once_with(
            1, 'partition', pool=None
        )
        autoscale.delete_servers_by_name.assert_called_once_with(
            ['server4'], pool=None
        )

    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale._query_stateapi')
    @mock.patch('treadmill.context.Context.admin')
    def test_scale_up_min_servers(self, admin_mock, stateapi_mock):
        """Test scaling up to min (active) servers."""

        mock_zkclient = context.GLOBAL.zk.conn
        mock_zkclient.get_children.return_value = []

        # Empty partition, min servers: 3 - create 3 servers.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 3, 'max_servers': 9}}},
            ],
            servers=[],
            servers_state=[],
            apps_state=[],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_called_once_with(
            3, 'partition', pool=None
        )
        autoscale.delete_servers_by_name.assert_not_called()

        autoscale.create_n_servers.reset_mock()
        autoscale.delete_servers_by_name.reset_mock()

        # 1 up, 1 down and 1 frozen server, min servers: 3 - create 2 servers.
        # Down and frozen servers have apps placed on them - don't delete.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 3, 'max_servers': 9}}},
            ],
            servers=[
                {'_id': 'server1', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server2', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server3', 'partition': 'partition',
                 '_create_timestamp': 100.0},
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
                ('server2', 'down', 100, 100, 100),
                ('server3', 'frozen', 100, 100, 100),
            ],
            apps_state=[
                ('proid.app#001', 'partition', 'server1'),
                ('proid.app#002', 'partition', 'server2'),
                ('proid.app#003', 'partition', 'server3'),
            ],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_called_once_with(
            2, 'partition', pool=None
        )
        autoscale.delete_servers_by_name.assert_not_called()

    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale._query_stateapi')
    @mock.patch('treadmill.context.Context.admin')
    def test_scale_down(self, admin_mock, stateapi_mock):
        """Test scaling down."""

        mock_zkclient = context.GLOBAL.zk.conn
        mock_zkclient.get_children.return_value = []

        # Pending apps: 1, idle servers: 2 - delete 1 server.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 3, 'max_servers': 9}}},
            ],
            servers=[
                {'_id': 'server1', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server2', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server3', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server4', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server5', 'partition': 'partition',
                 '_create_timestamp': 100.0},
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
                ('server2', 'up', 100, 100, 100),
                ('server3', 'up', 100, 100, 100),
                ('server4', 'up', 100, 100, 100),
                ('server5', 'up', 100, 100, 100),
            ],
            apps_state=[
                ('proid.app#001', 'partition', 'server1'),
                ('proid.app#002', 'partition', 'server2'),
                ('proid.app#003', 'partition', 'server3'),
                ('proid.app#004', 'partition', None),
            ],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_not_called()
        autoscale.delete_servers_by_name.assert_called_once_with(
            ['server4'], pool=None
        )

        autoscale.create_n_servers.reset_mock()
        autoscale.delete_servers_by_name.reset_mock()

        # No pending apps, idle servers: 5, min servers: 3 - delete 2 servers.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 3, 'max_servers': 9}}},
            ],
            servers=[
                {'_id': 'server1', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server2', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server3', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server4', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server5', 'partition': 'partition',
                 '_create_timestamp': 100.0},
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
                ('server2', 'up', 100, 100, 100),
                ('server3', 'up', 100, 100, 100),
                ('server4', 'up', 100, 100, 100),
                ('server5', 'up', 100, 100, 100),
            ],
            apps_state=[],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_not_called()
        autoscale.delete_servers_by_name.assert_called_once_with(
            ['server1', 'server2'], pool=None
        )

        autoscale.create_n_servers.reset_mock()
        autoscale.delete_servers_by_name.reset_mock()

        # Delete empty down and frozen servers.
        _mock_cell(
            admin_mock, stateapi_mock,
            partitions=[
                {'_id': 'partition',
                 'data': {'autoscale': {'min_servers': 3, 'max_servers': 9}}},
            ],
            servers=[
                {'_id': 'server1', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server2', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server3', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server4', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server5', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server6', 'partition': 'partition',
                 '_create_timestamp': 100.0},
                {'_id': 'server7', 'partition': 'partition',
                 '_create_timestamp': 100.0},
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
                ('server2', 'up', 100, 100, 100),
                ('server3', 'up', 100, 100, 100),
                ('server4', 'down', 100, 100, 100),
                ('server5', 'down', 100, 100, 100),
                ('server6', 'down', 100, 100, 100),
                ('server7', 'frozen', 100, 100, 100),
            ],
            apps_state=[
                ('proid.app#001', 'partition', 'server6'),
            ],
        )
        mock_zkclient.get_children.return_value = ['server5']

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_not_called()
        autoscale.delete_servers_by_name.assert_called_once_with(
            ['server4'], pool=None
        )

    @mock.patch('treadmill.context.Context.ldap',
                mock.Mock(url=['ldap://foo:1234']))
    @mock.patch('treadmill.context.Context.admin')
    @mock.patch('treadmill.syscall.krb5.get_host_realm',
                mock.Mock(return_value=['FOO.COM']))
    @mock.patch('treadmill_aws.hostmanager.create_host')
    @mock.patch('treadmill_aws.hostmanager.create_otp', mock.Mock())
    @mock.patch('treadmill_aws.awscontext.AWSContext.ec2', mock.Mock())
    @mock.patch('treadmill_aws.awscontext.AWSContext.sts', mock.Mock())
    @mock.patch('treadmill_aws.awscontext.AWSContext.ipaclient', mock.Mock())
    @mock.patch('time.time', mock.Mock(return_value=1000.0))
    @mock.patch('random.shuffle', mock.Mock(side_effect=lambda x: x))
    def test_create_n_servers(self, create_host_mock, admin_mock):
        """Test creating new servers in the cell."""
        admin_cell_mock = admin_mock.cell.return_value
        admin_cell_mock.get.return_value = {
            'data': {
                'image': 'ami-test',
                'size': 'm5.large',
                'subnets': ['subnet-4c76610a', 'subnet-4c76610b'],
                'secgroup': 'test',
                'hostgroups': ['test'],
                'instance_profile': 'test',
                'disk_size': '100',
                'aws_account': 'test',
            }
        }
        admin_part_mock = admin_mock.partition.return_value
        admin_part_mock.get.return_value = {
            'data': {
                'instance_types': ['m5.large', 'm5.xlarge'],
                'spot_instance_types': ['m5.large', 'm5.xlarge', 'm5.2xlarge'],
            }
        }

        # Create 3 on-demand hosts.
        hosts_created = autoscale.create_n_servers(3, 'partition')

        self.assertEqual(
            hosts_created,
            [
                {
                    'hostname': 'test-partition-8s6u9ns20000.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20001.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20002.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
            ]
        )

        create_host_mock.reset_mock()

        # Create 1 on-demand host and 2 spot hosts.
        hosts_created = autoscale.create_n_servers(
            3, 'partition', min_on_demand=1, max_on_demand=1
        )

        self.assertEqual(
            hosts_created,
            [
                {
                    'hostname': 'test-partition-8s6u9ns20000.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20001.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20002.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610a',
                },
            ]
        )

        create_host_mock.reset_mock()

        # Create 1 on-demand host and try 2 spot hosts, fallback to on-demand.
        create_host_mock.side_effect = lambda *args, **kwargs: _raise_if(
            kwargs['spot'],
            botoexc.ClientError(
                {'Error': {'Code': 'SpotMaxPriceTooLow'}}, None
            )
        )

        hosts_created = autoscale.create_n_servers(
            3, 'partition', min_on_demand=1, max_on_demand=3
        )

        self.assertEqual(
            hosts_created,
            [
                {
                    'hostname': 'test-partition-8s6u9ns20000.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20001.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20002.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
            ]
        )
        # Check if each spot type was tried once in each subnet, check order.
        self.assertEqual(
            [
                (kwargs['instance_type'], kwargs['subnet'])
                for _args, kwargs in create_host_mock.call_args_list
                if kwargs['spot']
            ],
            [
                ('m5.large', 'subnet-4c76610a'),
                ('m5.large', 'subnet-4c76610b'),
                ('m5.xlarge', 'subnet-4c76610a'),
                ('m5.xlarge', 'subnet-4c76610b'),
                ('m5.2xlarge', 'subnet-4c76610a'),
                ('m5.2xlarge', 'subnet-4c76610b'),
            ]
        )

        create_host_mock.reset_mock()

        # Create 1 on-demand host and try 2 spot hosts, no fallback - fail.
        with self.assertRaisesRegex(
                Exception,
                'Failed to create host test-partition-8s6u9ns20001.foo.com'
        ):
            hosts_created = autoscale.create_n_servers(
                3, 'partition', min_on_demand=1, max_on_demand=1
            )

        create_host_mock.reset_mock()

        # Create 1 on-demand host and 2 spot hosts, m5.large spot not feasible.
        create_host_mock.side_effect = lambda *args, **kwargs: _raise_if(
            kwargs['spot'] and kwargs['instance_type'] == 'm5.large',
            botoexc.ClientError(
                {'Error': {'Code': 'InsufficientInstanceCapacity'}}, None
            )
        )

        hosts_created = autoscale.create_n_servers(
            3, 'partition', min_on_demand=1, max_on_demand=1
        )

        self.assertEqual(
            hosts_created,
            [
                {
                    'hostname': 'test-partition-8s6u9ns20000.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20001.foo.com',
                    'type': 'm5.xlarge',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20002.foo.com',
                    'type': 'm5.xlarge',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610a',
                },
            ]
        )
        # Check if m5.large spot was tried once in each subnet, then m5.xlarge.
        self.assertEqual(
            [
                (kwargs['instance_type'], kwargs['subnet'])
                for _args, kwargs in create_host_mock.call_args_list
                if kwargs['spot']
            ],
            [
                ('m5.large', 'subnet-4c76610a'),
                ('m5.large', 'subnet-4c76610b'),
                ('m5.xlarge', 'subnet-4c76610a'),
                ('m5.xlarge', 'subnet-4c76610a'),
            ]
        )

        create_host_mock.reset_mock()

        # Create 1 on-demand host and 2 spot hosts, m5.large not feasible in
        # subnet-4c76610a, but feasible in subnet-4c76610b.
        create_host_mock.side_effect = lambda *args, **kwargs: _raise_if(
            (
                kwargs['instance_type'] == 'm5.large' and
                kwargs['subnet'] == 'subnet-4c76610a'
            ),
            botoexc.ClientError(
                {'Error': {'Code': 'InsufficientInstanceCapacity'}}, None
            )
        )

        hosts_created = autoscale.create_n_servers(
            3, 'partition', min_on_demand=1, max_on_demand=1
        )

        self.assertEqual(
            hosts_created,
            [
                {
                    'hostname': 'test-partition-8s6u9ns20000.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610b',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20001.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610b',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20002.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610b',
                },
            ]
        )
        # Check if subnet-4c76610a was tried once for on-demand and spot.
        self.assertEqual(
            [
                (kwargs['instance_type'], kwargs['spot'], kwargs['subnet'])
                for _args, kwargs in create_host_mock.call_args_list
            ],
            [
                ('m5.large', False, 'subnet-4c76610a'),
                ('m5.large', False, 'subnet-4c76610b'),
                ('m5.large', True, 'subnet-4c76610a'),
                ('m5.large', True, 'subnet-4c76610b'),
                ('m5.large', True, 'subnet-4c76610b'),
            ]
        )

        create_host_mock.reset_mock()

        # Create 1 on-demand host and 2 spot hosts, subnet-4c76610a exhausted.
        create_host_mock.side_effect = lambda *args, **kwargs: _raise_if(
            (
                kwargs['subnet'] == 'subnet-4c76610a'
            ),
            botoexc.ClientError(
                {'Error': {'Code': 'InsufficientFreeAddressesInSubnet'}}, None
            )
        )

        hosts_created = autoscale.create_n_servers(
            3, 'partition', min_on_demand=1, max_on_demand=1
        )

        self.assertEqual(
            hosts_created,
            [
                {
                    'hostname': 'test-partition-8s6u9ns20000.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610b',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20001.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610b',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20002.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610b',
                },
            ]
        )
        # Check if subnet-4c76610a was tried once (entire subnet excluded).
        self.assertEqual(
            [
                (kwargs['instance_type'], kwargs['spot'], kwargs['subnet'])
                for _args, kwargs in create_host_mock.call_args_list
            ],
            [
                ('m5.large', False, 'subnet-4c76610a'),
                ('m5.large', False, 'subnet-4c76610b'),
                ('m5.large', True, 'subnet-4c76610b'),
                ('m5.large', True, 'subnet-4c76610b'),
            ]
        )

        create_host_mock.reset_mock()

        # Create 1 on-demand host and 2 spot hosts, retry on InternalError.
        raise_err = {
            'test-partition-8s6u9ns20000.foo.com': True,
            'test-partition-8s6u9ns20001.foo.com': True,
            'test-partition-8s6u9ns20002.foo.com': True,
        }
        create_host_mock.side_effect = lambda *args, **kwargs: _raise_if(
            raise_err.pop(kwargs['hostname'], False),
            botoexc.ClientError(
                {'Error': {'Code': 'InternalError'}}, None
            )
        )

        hosts_created = autoscale.create_n_servers(
            3, 'partition', min_on_demand=1, max_on_demand=1
        )

        self.assertEqual(
            hosts_created,
            [
                {
                    'hostname': 'test-partition-8s6u9ns20000.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'on-demand',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20001.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610a',
                },
                {
                    'hostname': 'test-partition-8s6u9ns20002.foo.com',
                    'type': 'm5.large',
                    'lifecycle': 'spot',
                    'subnet': 'subnet-4c76610a',
                },
            ]
        )
        # Check retries.
        self.assertEqual(
            [
                (
                    kwargs['hostname'],
                    kwargs['instance_type'],
                    kwargs['spot'],
                    kwargs['subnet']
                )
                for _args, kwargs in create_host_mock.call_args_list
            ],
            [
                (
                    'test-partition-8s6u9ns20000.foo.com',
                    'm5.large', False, 'subnet-4c76610a'
                ),
                (
                    'test-partition-8s6u9ns20000.foo.com',
                    'm5.large', False, 'subnet-4c76610a'
                ),
                (
                    'test-partition-8s6u9ns20001.foo.com',
                    'm5.large', True, 'subnet-4c76610a'
                ),
                (
                    'test-partition-8s6u9ns20001.foo.com',
                    'm5.large', True, 'subnet-4c76610a'
                ),
                (
                    'test-partition-8s6u9ns20002.foo.com',
                    'm5.large', True, 'subnet-4c76610a'
                ),
                (
                    'test-partition-8s6u9ns20002.foo.com',
                    'm5.large', True, 'subnet-4c76610a'
                ),
            ]
        )

        create_host_mock.reset_mock()

    @mock.patch('treadmill.presence.kill_node')
    @mock.patch('treadmill.context.Context.ldap',
                mock.Mock(url=['ldap://foo:1234']))
    @mock.patch('treadmill.context.Context.admin')
    @mock.patch('treadmill_aws.hostmanager.delete_hosts')
    @mock.patch('treadmill_aws.awscontext.AWSContext.ec2', mock.Mock())
    @mock.patch('treadmill_aws.awscontext.AWSContext.ipaclient', mock.Mock())
    def test_delete_servers_by_name(self, delete_hosts_mock, admin_mock,
                                    kill_node_mock):
        """Test deleting servers by name."""
        admin_srv_mock = admin_mock.server.return_value

        autoscale.delete_servers_by_name([
            'test-partition-dq2opb2qrfj.foo.com',
            'test-partition-dq2opbqskkq.foo.com',
            'test-partition-dq2opc7ao37.foo.com',
        ])

        delete_hosts_mock.assert_called_once_with(
            ipa_client=mock.ANY,
            ec2_conn=mock.ANY,
            hostnames=[
                'test-partition-dq2opb2qrfj.foo.com',
                'test-partition-dq2opbqskkq.foo.com',
                'test-partition-dq2opc7ao37.foo.com',
            ],
        )
        admin_srv_mock.delete.assert_has_calls([
            mock.call('test-partition-dq2opb2qrfj.foo.com'),
            mock.call('test-partition-dq2opbqskkq.foo.com'),
            mock.call('test-partition-dq2opc7ao37.foo.com'),
        ])
        kill_node_mock.assert_has_calls([
            mock.call(mock.ANY, 'test-partition-dq2opb2qrfj.foo.com'),
            mock.call(mock.ANY, 'test-partition-dq2opbqskkq.foo.com'),
            mock.call(mock.ANY, 'test-partition-dq2opc7ao37.foo.com'),
        ])

    @mock.patch('treadmill.presence.kill_node')
    @mock.patch('treadmill.context.Context.ldap',
                mock.Mock(url=['ldap://foo:1234']))
    @mock.patch('treadmill.context.Context.admin')
    @mock.patch('treadmill_aws.hostmanager.delete_hosts')
    @mock.patch('treadmill_aws.awscontext.AWSContext.ec2', mock.Mock())
    @mock.patch('treadmill_aws.awscontext.AWSContext.ipaclient', mock.Mock())
    def test_delete_n_servers(self, delete_hosts_mock, admin_mock,
                              kill_node_mock):
        """Test deleting n servers."""
        admin_srv_mock = admin_mock.server.return_value
        admin_srv_mock.list.return_value = [
            {'_id': 'test-partition-dq2opb2qrfj.foo.com'},
            {'_id': 'test-partition-dq2opbqskkq.foo.com'},
            {'_id': 'test-partition-dq2opc7ao37.foo.com'},
        ]

        autoscale.delete_n_servers(2, partition='partition')

        delete_hosts_mock.assert_called_once_with(
            ipa_client=mock.ANY,
            ec2_conn=mock.ANY,
            hostnames=[
                'test-partition-dq2opb2qrfj.foo.com',
                'test-partition-dq2opbqskkq.foo.com',
            ],
        )
        admin_srv_mock.delete.assert_has_calls([
            mock.call('test-partition-dq2opb2qrfj.foo.com'),
            mock.call('test-partition-dq2opbqskkq.foo.com'),
        ])
        kill_node_mock.assert_has_calls([
            mock.call(mock.ANY, 'test-partition-dq2opb2qrfj.foo.com'),
            mock.call(mock.ANY, 'test-partition-dq2opbqskkq.foo.com'),
        ])
