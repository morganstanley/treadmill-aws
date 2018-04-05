"""
Unit test for VPC.
"""

import unittest
import mock
from treadmill_aws.infra import vpc


class VPCTest(unittest.TestCase):
    """Tests supervisor routines."""

    def setUp(self):
        self.vpc_id_mock = '786'
        self.subnet_id_mock = '111'
        self.gateway_id_mock = '007'
        self.route_table_id_mock = '411'
        self.security_group_id_mock = '777'
        self.internet_gateway_id_mock = '999'

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_init(self, conn_mock):
        """Test init."""
        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = conn_mock()
        _vpc = vpc.VPC()

        self.assertIsNone(_vpc.instance_id)

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_create(self, conn_mock):
        """Test create."""
        _conn_mock = conn_mock()
        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        vpc_response_mock = {
            'Vpc': {
                'VpcId': self.vpc_id_mock,
                'CidrBlock': '172.16.0.0/16'
            }
        }
        _conn_mock.create_vpc = mock.Mock(return_value=vpc_response_mock)
        _conn_mock.create_tags = mock.Mock()

        _vpc = vpc.VPC.create(name='VpcTest', cidr_block='172.16.0.0/16')

        self.assertEqual(_vpc.instance_id, self.vpc_id_mock)
        self.assertEqual(_vpc.metadata, vpc_response_mock['Vpc'])
        self.assertEqual(_vpc.cidr_block, '172.16.0.0/16')
        _conn_mock.create_vpc.assert_called_once_with(
            CidrBlock='172.16.0.0/16'
        )
        _conn_mock.create_tags.assert_called_once_with(
            Resources=[self.vpc_id_mock],
            Tags=[{
                'Key': 'Name',
                'Value': 'VpcTest'
            }]
        )
        _conn_mock.modify_vpc_attribute.assert_called_once_with(
            VpcId=self.vpc_id_mock,
            EnableDnsHostnames={
                'Value': True
            })

    @mock.patch('treadmill_aws.infra.subnet.Subnet')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_create_subnet(self, conn_mock, subnet_mock):
        """Test create subnet."""
        _conn_mock = conn_mock()
        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.create_subnet(
            name='subnet-name',
            cidr_block='172.23.0.0/24',
            gateway_id='gateway-id'
        )

        subnet_mock.create.assert_called_once_with(
            name='subnet-name',
            vpc_id=self.vpc_id_mock,
            cidr_block='172.23.0.0/24',
            gateway_id='gateway-id'
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_create_internet_gateway(self, conn_mock):
        """Test create internet gateway."""
        _conn_mock = conn_mock()
        _conn_mock.create_internet_gateway = mock.Mock(return_value={
            'InternetGateway': {
                'InternetGatewayId': self.gateway_id_mock
            }
        })
        _conn_mock.attach_internet_gatway = mock.Mock()

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.create_internet_gateway()

        self.assertEqual(_vpc.gateway_ids, [self.gateway_id_mock])
        _conn_mock.create_internet_gateway.assert_called_once()
        _conn_mock.attach_internet_gateway.assert_called_once_with(
            InternetGatewayId=self.gateway_id_mock,
            VpcId=self.vpc_id_mock
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_create_security_group(self, conn_mock):
        """Test create security group."""
        _conn_mock = conn_mock()
        _conn_mock.create_security_group = mock.Mock(return_value={
            'GroupId': self.security_group_id_mock
        })

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.create_security_group(
            group_name='foobar',
            description='foobar description'
        )

        self.assertEqual(_vpc.secgroup_ids, [self.security_group_id_mock])
        _conn_mock.create_security_group.assert_called_once_with(
            GroupName='foobar',
            Description='foobar description',
            VpcId=self.vpc_id_mock
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_add_secgrp_rules(self, conn_mock):
        """Test add security group rules."""
        _conn_mock = conn_mock()
        _conn_mock.authorize_security_group_ingress = mock.Mock()

        vpc.VPC.ec2_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.add_secgrp_rules(
            secgroup_id=self.security_group_id_mock,
            ip_permissions=[{
                'IpProtocol': '-1',
                'UserIdGroupPairs': [{'GroupId': self.security_group_id_mock}]
            }]
        )
        _conn_mock.authorize_security_group_ingress.assert_called_once_with(
            GroupId=self.security_group_id_mock,
            IpPermissions=[{
                'IpProtocol': '-1',
                'UserIdGroupPairs': [{'GroupId': self.security_group_id_mock}]
            }]
        )

    @mock.patch('treadmill_aws.infra.instances.connection.Connection')
    @mock.patch('treadmill_aws.infra.instances.Instances')
    @mock.patch('treadmill_aws.infra.vpc.instances.Instances')
    def test_get_instances(self, conn_mock, instances_mock,
                           vpc_instances_mock):
        """Test get instances."""
        _conn_mock = conn_mock()
        instances_mock.get = vpc_instances_mock.get = mock.Mock(
            return_value='foo'
        )
        conn_mock.describe_vpcs = mock.Mock(
            return_value={'Vpcs': [{'VpcId': self.vpc_id_mock, 'foo': 'bar'}]}
        )

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.get_instances(refresh=True)

        self.assertEqual(
            _vpc.instances,
            'foo'
        )

        instances_mock.get.assert_called_once_with(
            filters=[{
                'Name': 'vpc-id',
                'Values': [self.vpc_id_mock],
            }]
        )

    @mock.patch('treadmill_aws.infra.instances.connection.Connection')
    @mock.patch('treadmill_aws.infra.instances.Instances')
    @mock.patch('treadmill_aws.infra.vpc.instances.Instances')
    def test_terminate_instances(self, conn_mock, _instances_mock,
                                 _vpc_instances_mock):
        """Test terminate instances."""
        _conn_mock = conn_mock()
        instances_obj_mock = mock.Mock()
        conn_mock.describe_vpcs = mock.Mock(
            return_value={'Vpcs': [{'VpcId': self.vpc_id_mock, 'foo': 'bar'}]}
        )

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.instances = instances_obj_mock

        _vpc.terminate_instances()

        instances_obj_mock.terminate.assert_called_once_with()

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_load_security_group_ids(self, conn_mock):
        """Test load security group ids."""
        _conn_mock = conn_mock()
        _conn_mock.describe_security_groups = mock.Mock(return_value={
            'SecurityGroups': [{
                'GroupId': 'secgroup-id-0',
                'GroupName': 'foobar'
            }, {
                'GroupId': 'secgroup-id-1',
                'GroupName': 'default'
            }]
        })

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.load_security_group_ids()

        _conn_mock.describe_security_groups.assert_called_once_with(
            Filters=[{
                'Name': 'vpc-id',
                'Values': [self.vpc_id_mock]
            }]
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_delete_security_groups(self, conn_mock):
        """Test delete security groups."""
        _conn_mock = conn_mock()
        _conn_mock.delete_security_group = mock.Mock()

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.secgroup_ids = ['secgroup-id-0', 'secgroup-id-1']
        _vpc.load_security_group_ids = mock.Mock()
        _vpc.delete_security_groups()

        self.assertCountEqual(
            _conn_mock.delete_security_group.mock_calls,
            [
                mock.mock.call(GroupId='secgroup-id-0'),
                mock.mock.call(GroupId='secgroup-id-1')
            ]
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_load_route_related_ids(self, conn_mock):
        """Test load route related ids."""
        route_table_response_mock = {
            'RouteTables': [{
                'RouteTableId': 'route_table_id_0',
                'VpcId': self.vpc_id_mock,
                'Routes': [{
                    'GatewayId': 'gateway_id_0',
                    'InstanceId': 'route_instance_id_0',
                }],
                'Associations': [{
                    'RouteTableAssociationId': 'ass_id_0',
                    'RouteTableId': 'route_table_id_0',
                    'SubnetId': 'subnet_id_0',
                }]
            }, {
                'RouteTableId': 'route_table_id_1',
                'VpcId': self.vpc_id_mock,
                'Routes': [{
                    'GatewayId': 'gateway_id_1',
                    'InstanceId': 'route_instance_id_1',
                }],
                'Associations': [{
                    'RouteTableAssociationId': 'ass_id_1',
                    'RouteTableId': 'route_table_id_1',
                    'SubnetId': 'subnet_id_1',
                }]
            }]
        }

        _conn_mock = conn_mock()
        _conn_mock.describe_route_tables = mock.Mock(
            return_value=route_table_response_mock
        )
        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.load_route_related_ids()
        self.assertEqual(_vpc.association_ids, ['ass_id_0', 'ass_id_1'])
        self.assertEqual(_vpc.route_table_ids,
                         ['route_table_id_0', 'route_table_id_1'])
        self.assertEqual(_vpc.subnet_ids, ['subnet_id_0', 'subnet_id_1'])

        _conn_mock.describe_route_tables.assert_called_once_with(
            Filters=[{
                'Name': 'vpc-id',
                'Values': [self.vpc_id_mock]
            }]
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_delete_route_tables(self, conn_mock):
        """Test delete route tables."""
        _conn_mock = conn_mock()
        _conn_mock.disassociate_route_table = mock.Mock()
        _conn_mock.delete_route_table = mock.Mock()
        _conn_mock.delete_subnet = mock.Mock()

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.route_related_ids = 'foo'
        _vpc.association_ids = ['ass-id']
        _vpc.route_table_ids = ['route-table-id']
        _vpc.subnet_ids = ['subnet-id']
        _vpc.delete_route_tables()

        _conn_mock.disassociate_route_table.assert_called_once_with(
            AssociationId='ass-id'
        )

        _conn_mock.delete_route_table.assert_called_once_with(
            RouteTableId='route-table-id'
        )

        _conn_mock.delete_subnet.assert_called_once_with(
            SubnetId='subnet-id'
        )

    @mock.patch.object(vpc.VPC, 'delete_route_tables')
    @mock.patch.object(vpc.VPC, 'delete_security_groups')
    @mock.patch.object(vpc.VPC, 'delete_internet_gateway')
    @mock.patch.object(vpc.VPC, 'terminate_instances')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_delete(
            self,
            conn_mock,
            terminate_instances_mock,
            delete_internet_gateway_mock,
            delete_security_groups_mock,
            delete_route_tables_mock,
    ):
        """Test delete."""
        _conn_mock = conn_mock()
        _conn_mock.delete_vpc = mock.Mock()

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.metadata = {'DhcpOptionsId': '1'}
        _vpc.delete()

        terminate_instances_mock.assert_called_once()
        delete_internet_gateway_mock.assert_called_once()
        delete_security_groups_mock.assert_called_once()
        delete_route_tables_mock.assert_called_once()
        _conn_mock.delete_vpc.assert_called_once_with(
            VpcId=self.vpc_id_mock
        )
        _conn_mock.delete_dhcp_options.assert_called_once_with(
            DhcpOptionsId='1'
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_get_internet_gateway_id(self, conn_mock):
        """Test get gateway id."""
        _conn_mock = conn_mock()
        _conn_mock.describe_internet_gateways = mock.Mock(return_value={
            'InternetGateways': [
                {
                    'InternetGatewayId': self.internet_gateway_id_mock
                }
            ]
        })

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.load_internet_gateway_ids()

        self.assertEqual(_vpc.gateway_ids, [self.internet_gateway_id_mock])

        _conn_mock.describe_internet_gateways.assert_called_once_with(
            Filters=[{
                'Name': 'attachment.vpc-id',
                'Values': [self.vpc_id_mock]
            }]
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_delete_internet_gateway(self, conn_mock):
        """Test delete gateway."""
        _conn_mock = conn_mock()
        _conn_mock.delete_internet_gateway = mock.Mock()

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.gateway_ids = [self.internet_gateway_id_mock]
        _vpc.delete_internet_gateway()

        _conn_mock.delete_internet_gateway.assert_called_once_with(
            InternetGatewayId=self.internet_gateway_id_mock
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_associate_dhcp_options(self, conn_mock):
        """Test associated dhcp options."""
        conn_mock.context.domain = 'cloud.ms.com'
        _conn_mock = conn_mock()
        _conn_mock.create_dhcp_options = mock.Mock(return_value={
            'DhcpOptions': {
                'DhcpOptionsId': 'some-dhcp-id'
            }
        })
        _conn_mock.associate_dhcp_options = mock.Mock()

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.associate_dhcp_options()

        _conn_mock.create_dhcp_options.assert_called_once_with(
            DhcpConfigurations=[
                {
                    'Key': 'domain-name',
                    'Values': ['cloud.ms.com']
                },
            ]
        )
        _conn_mock.associate_dhcp_options.assert_called_once_with(
            DhcpOptionsId='some-dhcp-id',
            VpcId=self.vpc_id_mock
        )

    @mock.patch.object(vpc.VPC, 'get_instances')
    @mock.patch.object(vpc.VPC, 'load_security_group_ids')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_refresh(self,
                     conn_mock,
                     security_group_ids_mock,
                     instances_mock):
        """Test refresh."""
        _conn_mock = conn_mock()
        _vpc_metadata_mock = {
            'VpcId': self.vpc_id_mock,
            'CidrBlock': '172.0.0.1'
        }
        _conn_mock.describe_vpcs = mock.Mock(
            return_value={'Vpcs': [_vpc_metadata_mock]}
        )
        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        _vpc = vpc.VPC(instance_id=self.vpc_id_mock)
        _vpc.refresh()
        self.assertIsInstance(_vpc, vpc.VPC)
        self.assertEqual(_vpc.instance_id, self.vpc_id_mock)
        self.assertEqual(_vpc.metadata, _vpc_metadata_mock)
        self.assertEqual(_vpc.cidr_block, '172.0.0.1')
        _conn_mock.describe_vpcs.assert_called_once_with(
            VpcIds=[self.vpc_id_mock]
        )
        instances_mock.assert_called_once()
        security_group_ids_mock.assert_called_once()

    @mock.patch.object(vpc.VPC, 'associate_dhcp_options')
    @mock.patch.object(vpc.VPC, 'create_security_group')
    @mock.patch.object(vpc.VPC, 'create_internet_gateway')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_setup(self, conn_mock, create_internet_gateway_mock,
                   create_security_group_mock, _associate_dhcp_options_mock):
        """Test setup."""
        create_security_group_mock.return_value = 'sg-group'
        _conn_mock = conn_mock()
        _vpc_mock = vpc.VPC()
        vpc.VPC.create = mock.Mock(return_value=_vpc_mock)
        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock

        vpc.VPC.setup(
            name='VpcTest',
            cidr_block='172.23.0.0/24',
        )

        vpc.VPC.create.assert_called_once_with(
            name='VpcTest',
            cidr_block='172.23.0.0/24'
        )
        create_internet_gateway_mock.assert_called_once()
        create_security_group_mock.assert_called_once_with(
            'sg_common', 'Treadmill Security Group'
        )
        _conn_mock.authorize_security_group_ingress.assert_called_once_with(  # noqa
            GroupId='sg-group',
            IpPermissions=[{
                'IpProtocol': '-1',
                'UserIdGroupPairs': [{'GroupId': 'sg-group'}]
            }]
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_all(self, conn_mock):
        """Test all."""
        _conn_mock = conn_mock()
        _conn_mock.describe_vpcs = mock.Mock(return_value={
            'Vpcs': [
                {
                    'VpcId': '1',
                    'foo': 'bar'
                },
                {
                    'VpcId': '303',
                    'foo': 'bar'
                }
            ]
        })
        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        vpcs = vpc.VPC.all()
        self.assertCountEqual(map(type, vpcs), [vpc.VPC, vpc.VPC])
        self.assertCountEqual([v.instance_id for v in vpcs], ['1', '303'])
        _conn_mock.describe_vpcs.assert_called_once_with(VpcIds=[])

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_list_cells(self, conn_mock):
        """Test list cells."""
        _conn_mock = conn_mock()
        _conn_mock.describe_subnets = mock.Mock(return_value={
            'Subnets': [
                {
                    'SubnetId': '1'
                },
                {
                    'SubnetId': '2'
                }
            ]
        })

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock
        subnets = vpc.VPC(instance_id='vpc-123').list_cells()

        _conn_mock.describe_subnets.assert_called_once_with(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': ['vpc-123']
                }
            ]
        )
        self.assertEqual(subnets, ['1', '2'])

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_get_id_from_name(self, conn_mock):
        """Test get id from name."""
        _conn_mock = conn_mock()
        _conn_mock.describe_vpcs = mock.Mock(return_value={
            'Vpcs': [
                {
                    'VpcId': 'foo',
                    'ooo': 'joo'
                }
            ]
        })

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock

        self.assertEqual(vpc.VPC.get_id_from_name('vpc-name'), 'foo')

        _conn_mock.describe_vpcs.assert_called_once_with(
            Filters=[{
                'Name': 'tag:Name',
                'Values': ['vpc-name']
            }]
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_get_id_from_name_mul_vpcs(self, conn_mock):
        """Test get id from name mutliple vpcs."""
        _conn_mock = conn_mock()
        _conn_mock.describe_vpcs = mock.Mock(return_value={
            'Vpcs': [
                {
                    'VpcId': 'foo',
                    'ooo': 'joo'
                },
                {
                    'VpcId': 'foobar',
                    'ooo': 'jooooo'
                }
            ]
        })

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock

        with self.assertRaises(ValueError):
            vpc.VPC.get_id_from_name('vpc-name')

        _conn_mock.describe_vpcs.assert_called_once_with(
            Filters=[{
                'Name': 'tag:Name',
                'Values': ['vpc-name']
            }]
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_get_id_from_name_no_vpc(self, conn_mock):
        """Test get id from name no vpc."""
        _conn_mock = conn_mock()
        _conn_mock.describe_vpcs = mock.Mock(return_value={
            'Vpcs': []
        })

        vpc.VPC.ec2_conn = vpc.VPC.route53_conn = _conn_mock

        self.assertIsNone(vpc.VPC.get_id_from_name('vpc-name'))

        _conn_mock.describe_vpcs.assert_called_once_with(
            Filters=[{
                'Name': 'tag:Name',
                'Values': ['vpc-name']
            }]
        )

    @mock.patch('treadmill_aws.infra.connection.Connection')
    def test_delete_dhcp_options(self, conn_mock):
        """Test delete dhcp options."""
        _conn_mock = conn_mock()

        vpc.VPC.ec2_conn = _conn_mock
        _vpc = vpc.VPC(metadata={'DhcpOptionsId': '1'})

        _vpc.delete_dhcp_options()

        _conn_mock.delete_dhcp_options.assert_called_once_with(
            DhcpOptionsId='1'
        )


if __name__ == '__main__':
    unittest.main()
