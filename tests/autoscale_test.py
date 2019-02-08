"""Tests for autoscale."""

import unittest

import mock

from treadmill import context

from treadmill_aws import autoscale


def _mock_cell(admin_mock, stateapi_mock,
               partitions, servers, servers_state, apps_state):
    cell_admin_mock = admin_mock.cell.return_value
    server_admin_mock = admin_mock.server.return_value

    cell_admin_mock.get.return_value = {
        'partitions': partitions,
    }
    server_admin_mock.list.return_value = servers

    apps_columns = ['instance', 'partition', 'server']
    servers_columns = ['name', 'state', 'cpu', 'mem', 'disk']

    stateapi_mock.return_value = (
        {'columns': apps_columns, 'data': apps_state},
        {'columns': servers_columns, 'data': servers_state},
    )


class AutoscaleTest(unittest.TestCase):
    """Test autoscale."""

    def setUp(self):
        context.GLOBAL.cell = 'test'

    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale._query_stateapi')
    @mock.patch('treadmill.context.Context.admin')
    def test_scale_up_no_idle(self, admin_mock, stateapi_mock):
        """Test scaling up with no idle servers present."""

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
        autoscale.delete_servers_by_name.assert_called_once_with(['server4'])

    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale._query_stateapi')
    @mock.patch('treadmill.context.Context.admin')
    def test_scale_up_min_servers(self, admin_mock, stateapi_mock):
        """Test scaling up to min (active) servers."""

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
        autoscale.delete_servers_by_name.assert_called_once_with(['server4'])

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
            ['server1', 'server2']
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
            ],
            servers_state=[
                ('server1', 'up', 100, 100, 100),
                ('server2', 'up', 100, 100, 100),
                ('server3', 'up', 100, 100, 100),
                ('server4', 'down', 100, 100, 100),
                ('server5', 'frozen', 100, 100, 100),
            ],
            apps_state=[],
        )

        autoscale.scale(0.5)

        autoscale.create_n_servers.assert_not_called()
        autoscale.delete_servers_by_name.assert_called_once_with(
            ['server4', 'server5']
        )
