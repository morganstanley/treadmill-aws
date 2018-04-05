"""
Unit test for treadmill_aws.infra.
"""

import unittest
import mock

from treadmill_aws import infra


class InfraTest(unittest.TestCase):
    """Tests treadmill_aws.infra"""

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_create_iam_role(self, connection_mock):
        "Test create IAM role"
        iam_conn_mock = connection_mock()
        iam_conn_mock.create_role = mock.Mock(return_value='custom_role')
        role = infra.create_iam_role(name='foo')
        self.assertEqual(role, 'custom_role')
        iam_conn_mock.create_role.assert_called_once()
        iam_conn_mock.create_instance_profile.assert_called_once_with(
            InstanceProfileName='foo'
        )
        iam_conn_mock.add_role_to_instance_profile.assert_called_once_with(
            RoleName='foo',
            InstanceProfileName='foo'
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    @mock.patch('treadmill_aws.infra.create_iam_role')
    def test_get_iam_role(self, create_iam_role_mock, connection_mock):
        "Test get IAM role"
        iam_conn_mock = connection_mock()
        iam_conn_mock.get_role = mock.Mock(return_value='custom_role')
        role = infra.get_iam_role(
            name='Test_Role', create=False
        )
        self.assertEqual(role, 'custom_role')
        iam_conn_mock.get_role.assert_called_once_with(
            RoleName='Test_Role'
        )
        create_iam_role_mock.assert_not_called()
