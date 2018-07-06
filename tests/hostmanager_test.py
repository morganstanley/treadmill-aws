"""Tests for aws/hostmanager."""

import re
import unittest

import mock

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

    def test_create_host(self):
        """Test that hostname logic is processed correctly."""
        fake_ipa_response = {'result': {'result': {'randompassword': '123'}}}

        def _test(count, hostname):
            ec2_conn = mock.MagicMock()
            ipa_client = mock.MagicMock()
            ipa_client.enroll_host.return_value = fake_ipa_response

            return hostmanager.create_host(
                ec2_conn=ec2_conn,
                ipa_client=ipa_client,
                image_id='foo',
                key='foo',
                secgroup_ids='foo',
                instance_type='foo',
                subnet_id='foo',
                disk='foo',
                instance_vars=None,
                count=count,
                domain='foo.com',
                role='bar',
                hostname=hostname)

        # Case 1: Shortname defined, count = 1, returns FQDN
        result = _test(count=1,
                       hostname='host1')
        self.assertEqual(result, ['host1.foo.com'])

        # Case 2: Shortname defined, count >1, throws error
        with self.assertRaises(IndexError) as context:
            result = _test(count=2, hostname='host1')

        # Case 3: No hostname defined, count = 1, returns generated FQDN
        result = _test(count=1,
                       hostname=None)
        self.assertTrue(re.match(r'^bar-[0-9a-zA-Z]+.foo.com$', result[0]))

        # Case 4: Pattern defined, count = 1, returns generated FQDN
        result = _test(count=1,
                       hostname='foobar-{time}')
        self.assertTrue(re.match(r'^foobar-[0-9a-zA-Z]+.foo.com$', result[0]))

        # Case 5: Pattern defined, count >1, generated FQDNs unique
        result = _test(count=100,
                       hostname='foobar-{time}')
        self.assertTrue(len(result) == len(set(result)))

    def test_generate_hostname(self):
        """Test that generated hostnames are rendered correctly."""
        assert True
