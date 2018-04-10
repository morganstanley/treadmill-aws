"""
Unit test for EC2Object.
"""

import unittest
import mock

from treadmill_aws.infra import ec2object


class VPCTest(unittest.TestCase):
    """Tests supervisor routines."""

    def setUp(self):
        pass

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_ec2conn(self, _conn_mock):
        """Test lazy construction of ec2 connection."""
        # pylint: disable=protected-access
        ec2_obj = ec2object.EC2Object()
        self.assertIsNone(ec2_obj._ec2_conn)
        conn = ec2_obj.ec2_conn
        self.assertIsNotNone(conn)
        ec2_obj.ec2_conn = None
        self.assertIsNone(ec2_obj._ec2_conn)


if __name__ == '__main__':
    unittest.main()
