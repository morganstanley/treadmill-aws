"""Setup Treadmill node."""

from treadmill_aws.infra.setup import base_provision
from treadmill_aws.infra import configuration, constants, instances
from treadmill_aws.api import ipa


class Node(base_provision.BaseProvision):
    """Treadmill node provisioning and setup."""

    # TODO: understand how to avoid overriding arguments of inherited methods.
    #       should base.setup be renamed? it is public?
    # pylint: disable=arguments-differ
    def setup(
            self,
            image,
            key,
            tm_release,
            instance_type,
            app_root,
            with_api,
            ipa_admin_password,
            proid,
            subnet_name
    ):
        """Setup node."""
        ldap_hostname, zk_hostname = self.hostnames_for(roles=[
            constants.ROLES['LDAP'],
            constants.ROLES['ZOOKEEPER'],
        ])

        _ipa = ipa.API()
        _node_hostnames = self._hostname_cluster(count=1)

        for _idx in _node_hostnames:
            _node_h = _node_hostnames[_idx]
            otp = _ipa.add_host(hostname=_node_h)
            self.name = _node_h

            self.configuration = configuration.Node(
                tm_release=tm_release,
                app_root=app_root,
                ldap_hostname=ldap_hostname,
                otp=otp,
                with_api=with_api,
                hostname=_node_h,
                ipa_admin_password=ipa_admin_password,
                proid=proid,
                zk_url=self._zk_url(zk_hostname)
            )
            super().setup(
                image=image,
                count=1,
                key=key,
                instance_type=instance_type,
                subnet_name=subnet_name,
                sg_names=[constants.COMMON_SEC_GRP],
            )

    def destroy(self, instance_id=None):
        """Destroy node."""
        if instance_id:
            _instances = instances.Instances.get(ids=[instance_id])
        elif self.name:
            _instances = instances.Instances.get(
                filters=[
                    {
                        'Name': 'tag-key',
                        'Values': ['Name']
                    },
                    {
                        'Name': 'tag-value',
                        'Values': [self.name]
                    },
                ]
            )
        else:
            return

        _instances.terminate()
