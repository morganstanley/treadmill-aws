"""Tests for aws/hostmanager."""

import re
import time
import unittest

import mock

from treadmill_aws import awscontext
from treadmill_aws import hostmanager
from treadmill_aws import ipaclient


# pylint: disable=protected-access
class HostmanagerTest(unittest.TestCase):
    """Tests hostmanager interface"""

    def test_instance_tags(self):
        """Test that tags are rendered correctly."""
        # Test 1) Empty additional tag list
        self.assertEqual(
            hostmanager._instance_tags('host.foo.com', 'foo', []),
            [{'ResourceType': 'instance',
              'Tags': [{'Key': 'Name', 'Value': 'host.foo.com'},
                       {'Key': 'Role', 'Value': 'foo'}]}]
        )
        # Test 2) Additional Tags
        self.assertListEqual(
            hostmanager._instance_tags('host.foo.com', 'foo',
                                       [{'Key': 'bar', 'Value': 'baz'}]),
            [{'ResourceType': 'instance',
              'Tags': [{'Key': 'bar', 'Value': 'baz'},
                       {'Key': 'Name', 'Value': 'host.foo.com'},
                       {'Key': 'Role', 'Value': 'foo'}]}]
        )

    def test_create_host(self):
        """Test that hostname logic is processed correctly."""

        def _test(count, hostname):
            awscontext.GLOBAL = mock.MagicMock()
            ec2_conn = mock.MagicMock()
            ipa_client = mock.MagicMock()

            awscontext.GLOBAL.iam.list_account_aliases.return_value = {
                "AccountAliases": ["foo"]}
            ipa_client.enroll_host.return_value = {'randompassword': '123'}

            return hostmanager.create_host(
                ec2_conn=ec2_conn,
                ipa_client=ipa_client,
                image_id='foo',
                key='foo',
                secgroup_ids='foo',
                instance_type='foo',
                subnet=['foo'],
                disk='foo',
                instance_vars=None,
                count=count,
                domain='foo.com',
                role='bar',
                hostname=hostname,
                nshostlocation='baz'
            )

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

    @mock.patch('time.time', mock.Mock(return_value=1538429096.025851))
    def test_timestamp(self):
        """Test timestamp generation."""
        self.assertEqual('y.x', hostmanager.generate_hostname('x', 'y'))
        self.assertEqual(
            'y-dl7tpestdee.x',
            hostmanager.generate_hostname('x', 'y-{time}')
        )

        time.time.return_value = 1538429096.025851
        h1 = hostmanager.generate_hostname('x', 'y-{time}')

        time.time.return_value = 1538429096.02586
        h2 = hostmanager.generate_hostname('x', 'y-{time}')

        time.time.return_value = 1538429096.03
        h3 = hostmanager.generate_hostname('x', 'y-{time}')

        self.assertTrue(h1 < h2)
        self.assertTrue(h2 < h3)

    @mock.patch('treadmill_aws.ec2client.delete_instances')
    @mock.patch('treadmill_aws.hostmanager._EC2_DELETE_BATCH', 2)
    def test_delete_hosts(self, delete_instances_mock):
        """Test deleting hosts."""
        ipa_client_mock = mock.Mock()
        ipa_client_mock.get_dns_record.side_effect = ipaclient.NotFoundError

        hostmanager.delete_hosts(
            mock.Mock(),
            ipa_client_mock,
            [
                'test-partition-dq2opb2qrfj.foo.com',
                'test-partition-dq2opbqskkq.foo.com',
                'test-partition-dq2opc7ao37.foo.com',
            ]
        )

        delete_instances_mock.assert_has_calls([
            mock.call(
                ec2_conn=mock.ANY,
                hostnames=[
                    'test-partition-dq2opb2qrfj.foo.com',
                    'test-partition-dq2opbqskkq.foo.com',
                ]
            ),
            mock.call(
                ec2_conn=mock.ANY,
                hostnames=[
                    'test-partition-dq2opc7ao37.foo.com',
                ]
            ),
        ])
        ipa_client_mock.unenroll_host.assert_has_calls([
            mock.call('test-partition-dq2opb2qrfj.foo.com'),
            mock.call('test-partition-dq2opbqskkq.foo.com'),
            mock.call('test-partition-dq2opc7ao37.foo.com'),
        ])
