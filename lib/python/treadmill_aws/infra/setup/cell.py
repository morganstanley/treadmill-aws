"""Cell setup."""

import logging

from treadmill_aws.infra import vpc, subnet
from treadmill_aws.infra.setup import master, zookeeper

_LOGGER = logging.getLogger(__name__)


class Cell:
    """Cell setup."""

    def __init__(self, subnet_name, vpc_id):
        self.subnet_name = subnet_name
        self.vpc = vpc.VPC(instance_id=vpc_id)
        self.master = None
        self.output = None
        self.zookeeper = None

    def setup_zookeeper(self, name, key, image, instance_type,
                        subnet_cidr_block, ipa_admin_password, count,
                        proid):
        """Setup Zookeeper."""
        self.zookeeper = zookeeper.Zookeeper(
            name=name, vpc_id=self.vpc.instance_id
        )
        self.zookeeper.setup(
            count=count,
            image=image,
            key=key,
            cidr_block=subnet_cidr_block,
            instance_type=instance_type,
            ipa_admin_password=ipa_admin_password,
            proid=proid,
            subnet_name=self.subnet_name
        )

    def setup_master(self, name, key, count, image, instance_type,
                     tm_release, app_root, ipa_admin_password, proid,
                     subnet_cidr_block=None):
        """Setup master."""
        self.master = master.Master(name=name, vpc_id=self.vpc.instance_id,)
        self.master.setup(
            image=image,
            count=count,
            cidr_block=subnet_cidr_block,
            key=key,
            tm_release=tm_release,
            instance_type=instance_type,
            app_root=app_root,
            ipa_admin_password=ipa_admin_password,
            proid=proid,
            subnet_name=self.subnet_name
        )
        self.show()

    def show(self):
        """Show cell status."""
        self.output = subnet.Subnet(
            name=self.subnet_name,
            vpc_id=self.vpc.instance_id
        ).show()
        _LOGGER.info(self.output)
        return self.output
