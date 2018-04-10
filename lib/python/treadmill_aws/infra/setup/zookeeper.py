"""Setup Zookeeper server."""

from collections import OrderedDict

from treadmill_aws.infra.setup import base_provision
from treadmill_aws.infra import configuration
from treadmill_aws.infra import constants
from treadmill_aws.infra import exceptions
from treadmill_aws.infra import connection
from treadmill_aws.api import ipa


class Zookeeper(base_provision.BaseProvision):
    """Setup Zookeeper."""

    # TODO: understand how to avoid overriding arguments of inherited methods.
    #       should base.setup be renamed? it is public?
    # pylint: disable=arguments-differ
    def setup(self, image, key, cidr_block, instance_type,
              ipa_admin_password, proid, subnet_name, count=3):
        """Setup Zookeeper server."""
        del ipa_admin_password
        ldap_hostname, ipa_server_hostname = self.hostnames_for(
            roles=[
                constants.ROLES['IPA'],
                constants.ROLES['LDAP'],
            ]
        )

        if not ipa_server_hostname:
            raise exceptions.IPAServerNotFound()
        if not ldap_hostname:
            raise exceptions.LDAPNotFound()

        _ipa = ipa.API()
        _zk_hostnames = self._hostname_cluster(count=count)
        _cfg_data = self._construct_cfg_data(_zk_hostnames)

        for _idx in _zk_hostnames:
            _zk_h = _zk_hostnames[_idx]
            _otp = _ipa.add_host(hostname=_zk_h)
            _ipa.service_add('zookeeper', _zk_h, {
                'domain': connection.Connection.context.domain,
                'hostname': _zk_h,
            })
            self.name = _zk_h
            self.configuration = configuration.Zookeeper(
                ldap_hostname=ldap_hostname,
                ipa_server_hostname=ipa_server_hostname,
                hostname=_zk_h,
                otp=_otp,
                idx=_idx,
                proid=proid,
                cfg_data=_cfg_data
            )
            super().setup(
                image=image,
                count=1,
                cidr_block=cidr_block,
                key=key,
                instance_type=instance_type,
                subnet_name=subnet_name,
                sg_names=[constants.COMMON_SEC_GRP],
            )

    def _construct_cfg_data(self, hostnames):
        """Construct configuration data."""
        return '\n'.join(
            ['server.' + _h[0] + '=' + _h[1] + ':2888:3888'
             for _h in OrderedDict(sorted(hostnames.items())).items()]
        )
