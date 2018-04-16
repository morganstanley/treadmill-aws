"""EC2 Client tests."""

import unittest

import mock

import treadmill_aws
from treadmill_aws import ec2client


class EC2ClientTest(unittest.TestCase):
    """Tests EC2 client interface"""

    def test_build_tag_render(self):
        """Test that tags are rendered correctly."""
        hostname = 'host.foo.com'
        role = 'foo'

        rendered_tags = [{'ResourceType': 'instance',
                          'Tags': [{'Value': 'host.foo.com', 'Key': 'Name'},
                                   {'Value': 'foo', 'Key': 'role'}]}]
        print(rendered_tags)

        self.assertEqual(ec2client.build_tags(hostname, role), rendered_tags)

    def test_create_instance(self):
        """ Test create_instance call to AWS- tags, template correct to
            input variables
        """
        # Create test client with EC2 connection Mocked
        ec2_conn = mock.MagicMock()
        ec2client.create_instance(
            ec2_conn,
            hostname='host.foo.com',
            user_data='foo',
            image_id='ami-foo12345',
            instance_type='t2.micro',
            key='foo',
            role='foo',
            secgroup_ids='sg-foo12345',
            subnet_id='subnet-foo12345'
        )

        self.assertEqual(ec2_conn.run_instances.call_count, 1)
        ec2_conn.run_instances.assert_called_with(
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
                                         {'Key': 'role', 'Value': 'foo'}]}],
            UserData='foo'
        )

    @mock.patch('treadmill_aws.ec2client.get_instance_by_hostname',
                mock.Mock())
    def test_delete_single_host(self):
        """ Test delete_instance call to AWS with single hostname
        """
        ec2_conn = mock.MagicMock()
        treadmill_aws.ec2client.get_instance_by_hostname.return_value = {
            'InstanceId': 'i-0123456789'
        }

        ec2client.delete_instance(ec2_conn, hostname='host1.foo.com')

        self.assertEqual(ec2_conn.terminate_instances.call_count, 1)
        ec2_conn.terminate_instances.assert_called_with(
            InstanceIds=['i-0123456789'],
            DryRun=False
        )

    @mock.patch('treadmill_aws.ec2client.get_instance_by_hostname',
                mock.Mock(return_value=[]))
    def test_delete_nonexistant_host(self):
        """ Test delete_instance call to AWS with nonexistant hostname
        """
        ec2_conn = mock.MagicMock()
        ec2client.delete_instance(ec2_conn, hostname='host1.foo.com')
        self.assertEqual(ec2_conn.terminate_instances.call_count, 0)

    def test_get_matching_hostname(self):
        """ Test get_instance_by_hostname call to AWS with full hostname
        """
        ec2_conn = mock.MagicMock()
        ec2_conn.describe_instances = mock.MagicMock()

        # Simplified AWS result
        # TODO: this does not seem like correct test. Hostname is derived from
        #       tag (Name), not from instance_id.
        ec2_conn.describe_instances.return_value = {
            'Reservations': [
                {'Instances': [{'InstanceId': 'host1.foo.com'}]}
            ]
        }

        result = ec2client.get_instance_by_hostname(
            ec2_conn,
            hostname='host1.foo.com'
        )

        self.assertEqual(ec2_conn.describe_instances.call_count, 1)
        self.assertEqual(result, {'InstanceId': 'host1.foo.com'})

    def test_get_multiple_matches(self):
        """ Test get_instance_by_hostname call to AWS with full hostname
        """
        ec2_conn = mock.MagicMock()
        ec2_conn.describe_instances = mock.MagicMock()

        search_results = {
            'Reservations': [
                {'Instances': [{'InstanceId': 'host1.foo.com'},
                               {'InstanceId': 'host2.foo.com'}]}]}

        ec2_conn.describe_instances.return_value = search_results

        result = ec2client.list_instances(
            ec2_conn,
            match_hostname='foo.com'
        )

        self.assertEqual(ec2_conn.describe_instances.call_count, 1)
        self.assertEqual(
            result,
            [{'InstanceId': 'host1.foo.com'}, {'InstanceId': 'host2.foo.com'}]
        )

    def test_get_all_matches(self):
        """ Test get_instance_by_hostname call to AWS with full hostname
        """
        ec2_conn = mock.MagicMock()
        ec2_conn.describe_instances = mock.MagicMock()

        # Simplified AWS result
        search_results = {
            'Reservations': [
                {'Instances': [{'InstanceId': 'host1.foo.com'},
                               {'InstanceId': 'host2.foo.com'}]}]}

        ec2_conn.describe_instances.return_value = search_results

        result = ec2client.list_instances(ec2_conn, match_hostname='')

        self.assertEqual(ec2_conn.describe_instances.call_count, 1)
        self.assertEqual(
            result,
            [{'InstanceId': 'host1.foo.com'}, {'InstanceId': 'host2.foo.com'}]
        )


if __name__ == '__main__':
    unittest.main()
