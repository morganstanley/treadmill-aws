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

    def test_render_manifest(self):
        """Test that YAML is rendered correctly."""
        self.assertEqual(
            hostmanager.render_manifest({'otp': 'abc123',
                                         'hostname': 'host.foo.com'}),
            "#cloud-config\n'hostname': 'host.foo.com'\n'otp': 'abc123'\n"
        )
