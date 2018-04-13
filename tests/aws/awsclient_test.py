"""AWS Client tests."""

import unittest

import mock

from treadmill_aws.aws.server.awsclient import AWSClient
from treadmill_aws.aws.server.awsclient import build_tags


class AWSClientTest(unittest.TestCase):
    """Tests AWS client interface"""

    def test_build_tag_render(self):
        """Test that tags are rendered correctly."""
        hostname = 'host.foo.com'
        role = 'foo'

        rendered_tags = [{'ResourceType': 'instance',
                          'Tags': [{'Value': 'host.foo.com', 'Key': 'Name'},
                                   {'Value': 'FOO', 'Key': 'Role'}]}]
        self.assertEqual(build_tags(hostname, role), rendered_tags)

    # create_instance tests
    # Test create_instance call to AWS

    @mock.patch("treadmill_aws.infra.connection.Connection")
    def test_create_instance(self, _conn_mock):
        """ Test create_instance call to AWS- tags, template correct to
            input variables
        """
        # Create test client with EC2 connection Mocked
        client = AWSClient()
        client.ec2_conn = _conn_mock
        client.create_instance(domain='foo.com',
                               hostname='host.foo.com',
                               image_id='ami-foo12345',
                               instance_type='t2.micro',
                               key='foo',
                               otp='123456789',
                               proxy='http://proxy.foo.com:3128/',
                               role='foo',
                               secgroup_ids='sg-foo12345',
                               subnet_id='subnet-foo12345')

        assert _conn_mock.run_instances.call_count == 1
        _conn_mock.run_instances.assert_called_with(
            ImageId='ami-foo12345',
            InstanceType='t2.micro',
            KeyName='foo',
            MaxCount=1,
            MinCount=1,
            NetworkInterfaces=[{'Groups': ['sg-foo12345'],
                                'SubnetId': 'subnet-foo12345',
                                'DeviceIndex': 0}],
            TagSpecifications=[{'ResourceType': 'instance',
                                'Tags': [{'Key': 'Name',
                                          'Value': 'host.foo.com'},
                                         {'Key': 'Role', 'Value': 'FOO'}]}],
            UserData=('#!/bin/bash\n    '
                      'hostnamectl set-hostname host.foo.com\n    '
                      'echo "export http_proxy=http://proxy.foo.com:3128/"'
                      '         >> /etc/profile.d/http_proxy.sh\n    '
                      'echo "export NO_PROXY=localhost,169.254.169.254,'
                      '*.foo.com"         >> /etc/profile.d/http_proxy.sh\n  '
                      '  yum install -y ipa-client\n    '
                      'ipa-client-install     --no-krb5-offline-password     '
                      '--enable-dns-updates     --password=\'123456789\'     '
                      '--mkhomedir     --no-ntp     --unattended'))

    # delete_instance tests

    @mock.patch("treadmill_aws.infra.connection.Connection")
    def test_delete_single_host(self, _conn_mock):
        """ Test delete_instance call to AWS with single hostname
        """
        client = AWSClient()
        client.ec2_conn = _conn_mock
        client.get_instances_by_hostname = mock.MagicMock(
            return_value=[{'InstanceId': 'i-0123456789'}])

        client.delete_instance(hostname='host1.foo.com')

        assert _conn_mock.terminate_instances.call_count == 1
        _conn_mock.terminate_instances.assert_called_with(
            InstanceIds=['i-0123456789'], DryRun=False)

    @mock.patch("treadmill_aws.infra.connection.Connection")
    def test_delete_multiple_hosts(self, _conn_mock):
        """ Test delete_instance call to AWS with multiple hostnames
        """
        client = AWSClient()
        client.ec2_conn = _conn_mock
        client.get_instances_by_hostname = mock.MagicMock(
            return_value=[
                {'InstanceId': 'i-0123456789'},
                {'InstanceId': 'i-abcdefghi'}])

        client.delete_instance(hostname='hosts.foo.com')

        assert _conn_mock.terminate_instances.call_count == 2

    @mock.patch("treadmill_aws.infra.connection.Connection")
    def test_delete_nonexistant_host(self, _conn_mock):
        """ Test delete_instance call to AWS with nonexistant hostname
        """
        client = AWSClient()
        client.ec2_conn = _conn_mock
        client.get_instances_by_hostname = mock.MagicMock(
            return_value=[])

        client.delete_instance(hostname='host1.foo.com')

        assert _conn_mock.terminate_instances.call_count == 0

    # get_instances_by_hostname

    @mock.patch("treadmill_aws.infra.connection.Connection")
    def test_get_matching_hostname(self, _conn_mock):
        """ Test get_instances_by_hostname call to AWS with full hostname
        """
        client = AWSClient()
        client.ec2_conn = _conn_mock
        client.describe_instances = mock.MagicMock()

        # Simplified AWS result
        search_results = {
            'Reservations': [
                {'Instances': [{'InstanceId': 'host1.foo.com'}]}]}

        client.ec2_conn.describe_instances.return_value = search_results

        result = client.get_instances_by_hostname(hostname='host1.foo.com')

        assert _conn_mock.describe_instances.call_count == 1
        assert result == [{'InstanceId': 'host1.foo.com'}]

    # Test get_instances_by_hostname call to AWS with pattern
    @mock.patch("treadmill_aws.infra.connection.Connection")
    def test_get_multiple_matches(self, _conn_mock):
        """ Test get_instances_by_hostname call to AWS with full hostname
        """
        client = AWSClient()
        client.ec2_conn = _conn_mock
        client.describe_instances = mock.MagicMock()

        # Simplified AWS result
        search_results = {
            'Reservations': [
                {'Instances': [{'InstanceId': 'host1.foo.com'},
                               {'InstanceId': 'host2.foo.com'}]}]}

        client.ec2_conn.describe_instances.return_value = search_results

        result = client.get_instances_by_hostname(hostname='foo.com')

        assert _conn_mock.describe_instances.call_count == 1
        assert result == [{'InstanceId': 'host1.foo.com'},
                          {'InstanceId': 'host2.foo.com'}]

    # Test get_instances_by_hostname call to AWS with no pattern (return all)
    @mock.patch("treadmill_aws.infra.connection.Connection")
    def test_get_all_matches(self, _conn_mock):
        """ Test get_instances_by_hostname call to AWS with full hostname
        """
        client = AWSClient()
        client.ec2_conn = _conn_mock
        client.describe_instances = mock.MagicMock()

        # Simplified AWS result
        search_results = {
            'Reservations': [
                {'Instances': [{'InstanceId': 'host1.foo.com'},
                               {'InstanceId': 'host2.foo.com'}]}]}

        client.ec2_conn.describe_instances.return_value = search_results

        result = client.get_instances_by_hostname(hostname='')

        assert _conn_mock.describe_instances.call_count == 1
        assert result == [{'InstanceId': 'host1.foo.com'},
                          {'InstanceId': 'host2.foo.com'}]


if __name__ == '__main__':
    unittest.main()
