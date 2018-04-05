"""
Unit test for EC2 ldap.
"""

import unittest
import mock

from treadmill_aws.infra.setup.ldap import LDAP
from treadmill_aws.infra.setup.base_provision import BaseProvision
from treadmill_aws.infra import exceptions


class LDAPTest(unittest.TestCase):
    """Tests EC2 LDAP"""

    @mock.patch.object(BaseProvision,
                       'hostnames_for',
                       mock.Mock(return_value=[None]))
    @mock.patch('treadmill_aws.infra.connection.Connection',
                mock.Mock())
    def test_setup_ldap_no_ipa(self):
        """Test LDAP setup no IPA."""
        ldap = LDAP(
            name='ldap',
            vpc_id='vpc-id',
        )

        with self.assertRaises(exceptions.IPAServerNotFound) as err:
            ldap.setup(
                image='foo-123',
                count=1,
                cidr_block='cidr-block',
                key='some-key',
                instance_type='small',
                tm_release='release',
                app_root='app-root',
                ipa_admin_password='ipa_pass',
                proid='foobar',
                subnet_name='sub-name'
            )

        self.assertEqual(
            err.exception.message,
            'Please check if IPA Server is up and running.'
        )

    @mock.patch('time.time', mock.Mock(return_value=1000))
    @mock.patch('treadmill_aws.infra.subnet.Subnet')
    @mock.patch('treadmill_aws.api.ipa.API')
    @mock.patch('treadmill_aws.infra.configuration.LDAP')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    @mock.patch('treadmill_aws.infra.vpc.VPC')
    @mock.patch('treadmill_aws.infra.instances.Instances')
    def test_setup_ldap(self, instances_mock, vpc_mock,
                        connection_mock, ldap_configuration_mock,
                        ipa_api_mock, subnet_mock):
        """Test LDAP setup."""
        connection_mock.context.domain = 'domain'
        _ipa_api_mock = ipa_api_mock()
        _ipa_api_mock.add_host = mock.Mock(return_value='otp')
        instances_mock.get_hostnames_by_roles = mock.Mock(return_value={
            'IPA': 'ipa-hostname'
        })
        instance_mock = mock.Mock(private_ip='1.1.1.1')
        instances = mock.Mock(instances=[instance_mock])
        instances_mock.create = mock.Mock(return_value=instances)
        _vpc_id_mock = 'vpc-id'
        _vpc_mock = vpc_mock(instance_id=_vpc_id_mock)
        _vpc_mock.gateway_ids = [123]
        _vpc_mock.secgroup_ids = ['secgroup-id']
        _subnet_mock = mock.Mock(
            name='subnet-name',
            instance_id='subnet-id',
            vpc_id=_vpc_id_mock,
            persisted=False
        )
        subnet_mock.get = mock.Mock(return_value=_subnet_mock)
        _ldap_configuration_mock = ldap_configuration_mock()
        _ldap_configuration_mock.get_userdata = mock.Mock(
            return_value='user-data-script'
        )
        ldap = LDAP(
            name='ldap',
            vpc_id=_vpc_id_mock,
        )
        ldap.subnet_name = 'ldap-subnet-name'
        ldap.setup(
            image='foo-123',
            count=1,
            cidr_block='cidr-block',
            key='some-key',
            instance_type='small',
            tm_release='release',
            app_root='app-root',
            ipa_admin_password='ipa_pass',
            proid='foobar',
            subnet_name='sub-name',
        )

        self.assertEqual(ldap.subnet.instances, instances)
        _ipa_api_mock.add_host.assert_called_with(
            hostname='ldap1-1000.domain'
        )
        _ipa_api_mock.service_add.assert_called_with(
            'ldap',
            'ldap1-1000.domain',
            {
                'domain': 'domain',
                'hostname': 'ldap1-1000.domain'
            }
        )
        instances_mock.get_hostnames_by_roles.assert_called_with(
            vpc_id=mock.ANY,
            roles=['IPA']
        )
        instances_mock.create.assert_called_once_with(
            image='foo-123',
            name='ldap1-1000.domain',
            count=1,
            subnet_id='subnet-id',
            instance_type='small',
            secgroup_ids=['secgroup-id'],
            key_name='some-key',
            user_data='user-data-script',
            role='LDAP',
        )
        _vpc_mock.load_security_group_ids.assert_called_once_with(
            sg_names=['sg_common']
        )
        _subnet_mock.persist.assert_called_once_with(
            cidr_block='cidr-block',
            gateway_id=123
        )

        self.assertEqual(
            ldap_configuration_mock.mock_calls[1],
            mock.mock.call(
                hostname='ldap1-1000.domain',
                otp='otp',
                tm_release='release',
                app_root='app-root',
                ipa_admin_password='ipa_pass',
                ipa_server_hostname='ipa-hostname',
                proid='foobar',
            )
        )
        _ldap_configuration_mock.get_userdata.assert_called_once()

    @mock.patch('treadmill_aws.infra.subnet.Subnet')
    @mock.patch('treadmill_aws.infra.connection.Connection')
    @mock.patch('treadmill_aws.infra.vpc.VPC')
    @mock.patch('treadmill_aws.infra.instances.Instances')
    def test_ldap_destroy(self, instances_mock, _vpc_mock, _connection_mock,
                          subnet_mock):
        """Test LDAP destroy."""
        _subnet_mock = subnet_mock(name='subnet-name')
        _subnet_mock.instances = mock.Mock(instances=[
            mock.Mock(private_ip='1.1.1.1')
        ])

        instances_mock.get_hostnames_by_roles = mock.Mock(return_value={
            'LDAP': 'ldap1-1000.domain'
        })

        ldap = LDAP(
            vpc_id='vpc-id',
            name='ldap'
        )
        ldap.destroy(
            subnet_name='subnet-name'
        )
        _subnet_mock.destroy.assert_called_once_with(role='LDAP')


if __name__ == '__main__':
    unittest.main()
