"""Tests for aws/hostmanager."""

import unittest

from treadmill_aws import hostmanager


# pylint: disable=protected-access
class HostmanagerTest(unittest.TestCase):
    """Tests hostmanager interface"""

    def test_instance_tags(self):
        """Test that tags are rendered correctly."""
        self.assertEqual(
            hostmanager._instance_tags('host.foo.com', 'foo'),
            [{'ResourceType': 'instance',
              'Tags': [{'Key': 'Name', 'Value': 'host.foo.com'},
                       {'Key': 'Role', 'Value': 'foo'}]}]
        )
