"""Tests for autoscale."""

import unittest

import mock

from treadmill_aws import autoscale


# pylint: disable=protected-access
class AutoscaleTest(unittest.TestCase):
    """Tests autoscale."""

    @mock.patch('treadmill_aws.autoscale._state', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    def test_scale_up_no_idle(self):
        """Test scale up."""
        autoscale._state.return_value = autoscale._STATE(
            running=10,
            pending=100,
            busy_srv_cnt=5,
            idle_servers=[],
        )

        self.assertEqual(
            (10, []),
            autoscale.scale(
                min_servers=0,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        self.assertEqual(
            (1, []),
            autoscale.scale(
                min_servers=0,
                max_servers=6,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        self.assertEqual(
            (0, []),
            autoscale.scale(
                min_servers=0,
                max_servers=5,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        autoscale._state.return_value = autoscale._STATE(
            running=10,
            pending=2,
            busy_srv_cnt=5,
            idle_servers=[],
        )

        self.assertEqual(
            (1, []),
            autoscale.scale(
                min_servers=0,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        autoscale._state.return_value = autoscale._STATE(
            running=1000,
            pending=1,
            busy_srv_cnt=10,
            idle_servers=[],
        )

        self.assertEqual(
            (1, []),
            autoscale.scale(
                min_servers=0,
                max_servers=2000,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

    @mock.patch('treadmill_aws.autoscale._state', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    def test_scale_up_with_idle(self):
        """Test scale up with some idle servers present."""
        autoscale._state.return_value = autoscale._STATE(
            running=10,
            pending=100,
            busy_srv_cnt=5,
            idle_servers=['a', 'b'],
        )

        self.assertEqual(
            (10, []),
            autoscale.scale(
                min_servers=0,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        # Two apps, two server idle, with current ratio .5, will not ask for
        # new servers.
        autoscale._state.return_value = autoscale._STATE(
            running=10,
            pending=2,
            busy_srv_cnt=5,
            idle_servers=['a', 'b'],
        )

        self.assertEqual(
            (0, []),
            autoscale.scale(
                min_servers=0,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        # 6 pending apps, two server idle, with current ratio .5. expect
        # additional 1 server.
        autoscale._state.return_value = autoscale._STATE(
            running=10,
            pending=6,
            busy_srv_cnt=5,
            idle_servers=['a', 'b'],
        )

        self.assertEqual(
            (1, []),
            autoscale.scale(
                min_servers=0,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

    @mock.patch('treadmill_aws.autoscale._state', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.delete_servers_by_name', mock.Mock())
    @mock.patch('treadmill_aws.autoscale.create_n_servers', mock.Mock())
    def test_scale_down(self):
        """Test scale down."""

        autoscale._state.return_value = autoscale._STATE(
            running=10,
            pending=1,
            busy_srv_cnt=5,
            idle_servers=['a', 'b'],
        )

        self.assertEqual(
            (0, ['a']),
            autoscale.scale(
                min_servers=0,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        autoscale._state.return_value = autoscale._STATE(
            running=10,
            pending=1,
            busy_srv_cnt=5,
            idle_servers=['a'],
        )

        self.assertEqual(
            (0, []),
            autoscale.scale(
                min_servers=0,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        autoscale._state.return_value = autoscale._STATE(
            running=10,
            pending=0,
            busy_srv_cnt=5,
            idle_servers=['a', 'b', 'c'],
        )

        self.assertEqual(
            (0, ['a', 'b', 'c']),
            autoscale.scale(
                min_servers=0,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        # There are 5 busy servers, so with 5 min servers, all idle will be
        # removed.
        self.assertEqual(
            (0, ['a', 'b', 'c']),
            autoscale.scale(
                min_servers=5,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )

        # There are 5 busy servers, so with 6 min servers, two idle will be
        # removed.
        self.assertEqual(
            (0, ['b', 'c']),
            autoscale.scale(
                min_servers=6,
                max_servers=200,
                default_app_srv_ratio=0.5,
                max_batch=10
            )
        )
