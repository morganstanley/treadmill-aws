"""Base class for provisioning AWS entities."""

import time

from treadmill_aws.infra import instances
from treadmill_aws.infra import connection
from treadmill_aws.infra import vpc
from treadmill_aws.infra import subnet
from treadmill_aws.infra import constants


class BaseProvision:
    """Base class for provisioning AWS entities."""

    def __init__(
            self,
            name,
            vpc_id
    ):
        self.name = name
        self.vpc = vpc.VPC(instance_id=vpc_id)
        self.ec2_conn = connection.Connection()
        _role = constants.ROLES.get(
            self.__class__.__name__.upper(),
            'DEFAULT'
        )
        self.role = _role
        self.subnet = None
        self.configuration = None

    def hostnames_for(self, roles):
        """Return hostnames for given role."""
        _result = instances.Instances.get_hostnames_by_roles(
            vpc_id=self.vpc.instance_id,
            roles=roles
        )

        return [_result.get(_r) for _r in roles]

    def setup(
            self,
            image,
            count,
            key,
            instance_type,
            subnet_name,
            sg_names,
            cidr_block=None,
    ):
        """Setup server."""
        if not self.subnet:
            self.subnet = subnet.Subnet.get(
                name=subnet_name,
                vpc_id=self.vpc.instance_id
            )

        self.subnet._name = subnet_name  # pylint: disable=protected-access

        if not self.subnet.persisted and not cidr_block:
            raise Exception(
                'Subnet CIDR block required for creating new subnet'
            )

        if not self.subnet.persisted:
            self.vpc.load_internet_gateway_ids()
            self.subnet.persist(
                cidr_block=cidr_block,
                gateway_id=self.vpc.gateway_ids[0]
            )

        user_data = ''
        if getattr(self, 'configuration', None):
            self.configuration.subnet_id = self.subnet.instance_id
            user_data = self.configuration.get_userdata()

        self.vpc.load_security_group_ids(sg_names=sg_names)

        self.subnet.instances = instances.Instances.create(
            name=self.name,
            image=image,
            count=count,
            subnet_id=self.subnet.instance_id,
            instance_type=instance_type,
            key_name=key,
            secgroup_ids=self.vpc.secgroup_ids,
            user_data=user_data,
            role=self.role
        )

    def destroy(self, subnet_name=None):
        """Destroy server."""
        if subnet_name:
            self.subnet = subnet.Subnet(
                name=subnet_name, vpc_id=self.vpc.instance_id
            )
            self.subnet.destroy(role=self.role)
        else:
            _instances = instances.Instances.get_by_roles(
                vpc_id=self.vpc.instance_id,
                roles=[self.role]
            )

            _subnet_ids = set(_i.subnet_id for _i in _instances.instances)

            _instances.terminate()

            for _id in _subnet_ids:
                subnet.Subnet(instance_id=_id).destroy(role=self.role)

    # TODO: show is inappropriate name, should it be "get"?
    def show(self):
        """Show parameters."""
        return self.subnet.show()

    def _hostname_cluster(self, count):
        """Return hostnames for a cluster of given count."""
        _hostnames = {}
        for _idx in range(0, count):
            _idx_s = str(_idx + 1)
            _hostnames[_idx_s] = self.name + _idx_s + '-' + str(
                time.time()
            ) + '.' + connection.Connection.context.domain

        return _hostnames

    def _zk_url(self, hostname):
        """Return Zookeper connection string."""
        # TODO: how is it base, and this method implementation is fishy.
        return 'zookeeper://foo@' + ','.join([
            _zk_h.strip() + ':' + str(constants.ZK_CLIENT_PORT)
            for _zk_h in hostname.split(',')
        ])
