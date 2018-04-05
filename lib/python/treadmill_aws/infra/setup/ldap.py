"""AWS setup for LDAP server."""

from treadmill_aws.infra.setup import base_provision
from treadmill_aws.infra import configuration
from treadmill_aws.infra import constants
from treadmill_aws.infra import exceptions
from treadmill_aws.infra import connection
from treadmill_aws.api import ipa


class LDAP(base_provision.BaseProvision):
    """LDAP provisioning."""

    # TODO: understand how to avoid overriding arguments of inherited methods.
    #       should base.setup be renamed? it is public?
    # pylint: disable=arguments-differ
    def setup(
            self,
            image,
            count,
            key,
            cidr_block,
            tm_release,
            instance_type,
            app_root,
            ipa_admin_password,
            proid,
            subnet_name,
    ):
        """Setup IPA server."""
        ipa_server_hostname, = self.hostnames_for(
            roles=[constants.ROLES['IPA']]
        )

        if not ipa_server_hostname:
            raise exceptions.IPAServerNotFound()

        _ldap_hostnames = self._hostname_cluster(count=count)
        _ipa = ipa.API()

        for _idx in _ldap_hostnames:
            _ldap_h = _ldap_hostnames[_idx]
            otp = _ipa.add_host(hostname=_ldap_h)
            _ipa.service_add('ldap', _ldap_h, {
                'domain': connection.Connection.context.domain,
                'hostname': _ldap_h,
            })
            self.name = _ldap_h
            self.configuration = configuration.LDAP(
                tm_release=tm_release,
                app_root=app_root,
                hostname=_ldap_h,
                ipa_admin_password=ipa_admin_password,
                ipa_server_hostname=ipa_server_hostname,
                otp=otp,
                proid=proid
            )
            super().setup(
                image=image,
                count=count,
                cidr_block=cidr_block,
                key=key,
                instance_type=instance_type,
                subnet_name=subnet_name,
                sg_names=[constants.COMMON_SEC_GRP],
            )
