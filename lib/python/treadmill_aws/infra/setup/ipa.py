"""Setup IPA server."""

import logging

import polling

import treadmill_aws
from treadmill_aws.infra.setup import base_provision
from treadmill_aws.infra import configuration, constants

_LOGGER = logging.getLogger(__name__)


class IPA(base_provision.BaseProvision):
    """Provision IPA server."""

    def __init__(self, *args, **kwargs):
        self._instances = None
        super().__init__(*args, **kwargs)

    @property
    def instances(self):
        """Return IPA instances."""
        if not self._instances:
            self.subnet.refresh()
            self.subnet.get_instances(
                refresh=True,
                role=constants.ROLES['IPA']
            )
            self._instances = self.subnet.instances

        return self._instances

    # TODO: understand how to avoid overriding arguments of inherited methods.
    #       should base.setup be renamed? it is public?
    # pylint: disable=arguments-differ
    def setup(
            self,
            image,
            count,
            cidr_block,
            ipa_admin_password,
            tm_release,
            key,
            instance_type,
            proid,
            subnet_name,
    ):
        """Setup IPA server."""
        treadmill_aws.infra.get_iam_role(
            name=constants.IPA_EC2_IAM_ROLE,
            create=True
        )

        secgroup_id = self.vpc.create_security_group(
            constants.IPA_SEC_GRP, 'IPA Security Group'
        )
        ip_permissions = [{
            'IpProtocol': 'tcp',
            'FromPort': constants.IPA_API_PORT,
            'ToPort': constants.IPA_API_PORT,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }]
        self.vpc.add_secgrp_rules(ip_permissions, secgroup_id)

        _ipa_hostnames = self._hostname_cluster(count=count)

        for _idx in _ipa_hostnames:
            _ipa_h = _ipa_hostnames[_idx]
            self.name = _ipa_h

            self.configuration = configuration.IPA(
                hostname=_ipa_h,
                vpc=self.vpc,
                ipa_admin_password=ipa_admin_password,
                tm_release=tm_release,
                proid=proid
            )
            super().setup(
                image=image,
                count=count,
                cidr_block=cidr_block,
                key=key,
                instance_type=instance_type,
                subnet_name=subnet_name,
                sg_names=[constants.COMMON_SEC_GRP, constants.IPA_SEC_GRP],
            )

        def check_passed_status():
            """Check IPA server status."""
            _LOGGER.info('Checking IPA server running status...')
            return all(
                map(
                    lambda i: i.running_status(refresh=True) == 'passed',
                    self.instances.instances
                )
            )

        polling.poll(
            check_passed_status,
            step=10,
            timeout=600
        )
        self.vpc.associate_dhcp_options(default=True)

        try:
            self.vpc.delete_dhcp_options()
        except Exception:  # pylint: disable=broad-except
            # TODO: no logging, exception too broad.
            pass

        self.vpc.associate_dhcp_options([
            {
                'Key': 'domain-name-servers',
                'Values': [
                    i.metadata['PrivateIpAddress']
                    for i in self.instances.instances
                ]
            }
        ])

    # TODO: understand how to avoid overriding arguments of inherited methods.
    #       should base.setup be renamed? it is public?
    # pylint: disable=arguments-differ
    # pylint: disable=signature-differs
    def destroy(self, subnet_name):
        """Destroy IPA server."""
        super().destroy(
            subnet_name=subnet_name
        )
        self.vpc.delete_security_groups(sg_names=[constants.IPA_SEC_GRP])
