"""EC2 subnet."""

import logging

from treadmill_aws.infra import ec2object
from treadmill_aws.infra import connection
from treadmill_aws.infra import constants
from treadmill_aws.infra import instances


_LOGGER = logging.getLogger(__name__)


class Subnet(ec2object.EC2Object):
    """EC2 subnet."""

    def __init__(self, name=None, instance_id=None, metadata=None,
                 vpc_id=None, instances_=None):
        super().__init__(
            name=name,
            instance_id=instance_id,
            metadata=metadata
        )
        self.vpc_id = vpc_id
        self.instances = instances_
        self.association_id = None
        self.route_table_id = None

    @classmethod
    def _load_json(cls, vpc_id, name, restrict_one=True):
        """Load json metadata."""
        _ec2_conn = connection.Connection()
        _json = _ec2_conn.describe_subnets(
            Filters=[
                {
                    'Name': 'vpc-id',
                    'Values': [vpc_id]
                },
                {
                    'Name': 'tag:Name',
                    'Values': [name]
                }
            ]
        )['Subnets']

        if restrict_one:
            if len(_json) > 1:
                raise ValueError('Multiple Subnets with name: ' + name)
            elif _json:
                return _json[0]
            else:
                raise ValueError('Empty subnet data: ' + name)
        else:
            return _json

    @classmethod
    def get(cls, vpc_id, name, restrict_one=True):
        """Get subnet."""
        _metadata = cls._load_json(
            vpc_id=vpc_id,
            name=name,
            restrict_one=restrict_one
        )

        return Subnet(
            metadata=_metadata,
            vpc_id=vpc_id,
        )

    @classmethod
    def create(cls, cidr_block, vpc_id, name, gateway_id):
        """Create subnet."""
        metadata = cls._create(cidr_block, vpc_id, name, gateway_id)
        _subnet = Subnet(
            name=name,
            metadata=metadata,
            vpc_id=vpc_id
        )
        _subnet.create_tags()
        # pylint: disable=protected-access
        _subnet._create_route_table(gateway_id)
        return _subnet

    @classmethod
    def _create(cls, cidr_block, vpc_id, name, gateway_id):
        """Helper method for creating subnet."""
        del gateway_id
        del name

        _ec2_conn = connection.Connection()
        return _ec2_conn.create_subnet(
            VpcId=vpc_id,
            CidrBlock=cidr_block,
            AvailabilityZone=Subnet._availability_zone()
        )['Subnet']

    @property
    def persisted(self):
        """Check if persisted."""
        return True if (
            self.metadata and self.metadata.get('SubnetId')
        ) else False

    def persist(self, cidr_block, gateway_id):
        """Persist subnet."""
        # TODO: what is persist? Save?
        self.metadata = Subnet._create(
            cidr_block=cidr_block,
            gateway_id=gateway_id,
            name=self.name,
            vpc_id=self.vpc_id
        )
        self.create_tags()
        self._create_route_table(gateway_id)

    def load_route_related_ids(self):
        """Load route related ids."""
        response = self.ec2_conn.describe_route_tables(
            Filters=self._association_filters()
        )
        self.association_id = self._get_ids_from_associations(
            response['RouteTables'],
            'RouteTableAssociationId'
        )[0]
        self.route_table_id = self._get_ids_from_associations(
            response['RouteTables'],
            'RouteTableId'
        )[0]

    def destroy(self, role=None):
        """Destroy subnet."""
        self.refresh()
        self.terminate_instances(role)

        remaining_instances = self._get_instances_by_filters(
            filters=self._network_filters()
        ).instances

        if not remaining_instances:
            self.load_route_related_ids()
            self.ec2_conn.disassociate_route_table(
                AssociationId=self.association_id
            )
            self.ec2_conn.delete_route_table(
                RouteTableId=self.route_table_id
            )
            self.ec2_conn.delete_subnet(
                SubnetId=self.instance_id
            )
        else:
            _LOGGER.info('keeping the subnet as other instances are alive.')
            return

    def get_instances(self, refresh=False, role=None):
        """Get instances in the subnet, optionally filter by role."""
        if role:
            self.get_instances_by_role(refresh=refresh, role=role)
        else:
            self.get_all_instances(refresh=refresh)

    def get_all_instances(self, refresh=False):
        """Get all instances."""
        if refresh or not self.instances:
            self.instances = self._get_instances_by_filters(
                filters=self._network_filters()
            )

    def _get_instances_by_filters(self, filters):
        """Return instances filters."""
        return instances.Instances.get(
            filters=filters
        )

    def get_instances_by_role(self, role, refresh=False):
        """Get instances given a role."""
        if refresh or not self.instances:
            self.instances = self._get_instances_by_filters(
                filters=self._network_filters(
                    extra_filters=self._role_filter(role)
                )
            )

    def terminate_instances(self, role):
        """Terminate instances of given role."""
        if not self.instances:
            self.get_instances(refresh=True, role=role)

        self.instances.terminate()

    def refresh(self):
        """Refresh."""
        if self.instance_id:
            self.metadata = self.ec2_conn.describe_subnets(
                SubnetIds=[self.instance_id]
            )['Subnets'][0]
            self.vpc_id = self.metadata.get('VpcId', None)
        else:
            self.metadata = Subnet._load_json(
                name=self.name,
                vpc_id=self.vpc_id
            )

    def show(self, role=None):
        """Show subnet details."""
        self.refresh()
        self.get_instances(refresh=True, role=role)
        _instance_details = None
        if self.instances:
            _instance_defaults = [
                self._instance_details(inst)
                for inst in self.instances.instances
            ]

        return {
            'VpcId': self.vpc_id,
            'SubnetId': self.instance_id,
            'Instances': _instance_details
        }

    def _create_route_table(self, gateway_id):
        """Create route table."""
        route_table = self.ec2_conn.create_route_table(VpcId=self.vpc_id)
        self.route_table_id = route_table['RouteTable']['RouteTableId']
        self.ec2_conn.create_route(
            RouteTableId=self.route_table_id,
            DestinationCidrBlock=constants.DESTINATION_CIDR_BLOCK,
            GatewayId=gateway_id
        )
        self.ec2_conn.associate_route_table(
            SubnetId=self.instance_id,
            RouteTableId=self.route_table_id
        )

    def _instance_details(self, instance):
        """Return instance details."""
        return {
            'Name': instance.name,
            'Role': instance.role,
            'HostName': instance.hostname,
            'InstanceId': instance.instance_id,
            'InstanceState': instance.metadata['State']['Name'],
            'SecurityGroups': instance.metadata['SecurityGroups'],
            'SubnetId': instance.metadata['SubnetId'],
            'PublicIpAddress': instance.metadata.get('PublicIpAddress', None),
            'PrivateIpAddress': instance.metadata.get(
                'PrivateIpAddress', None
            ),
            'InstanceType': instance.metadata.get('InstanceType', None),
        }

    def _select_from_tags(self, tags, selector):
        """Select from tags."""
        for tag in tags:
            if tag['Key'] == selector:
                return tag['Value']
        return None

    @classmethod
    def _availability_zone(cls):
        """Return availability zones."""
        _map = {
            "us-east-1": "us-east-1a",
            "us-east-2": "us-east-2a",
            "ap-southeast-1": "ap-southeast-1a",
            "ap-southeast-2": "ap-southeast-2a",
            "us-west-1": "us-west-1b",
            "us-west-2": "us-west-2a"
        }

        return _map.get(connection.Connection.context.region_name, None)

    def _role_filter(self, role):
        """Return role filters."""
        return [
            {
                'Name': 'tag-key',
                'Values': ['Role']
            },
            {
                'Name': 'tag-value',
                'Values': [role]
            }
        ]

    def _association_filters(self):
        """Return association filters."""
        return [{
            'Name': 'association.subnet-id',
            'Values': [self.instance_id]
        }]

    def _network_filters(self, extra_filters=None):
        """Return network filters."""
        default_filters = [{
            'Name': 'network-interface.subnet-id',
            'Values': [self.instance_id]
        }]

        if extra_filters:
            return default_filters + extra_filters
        else:
            return default_filters

    def _get_ids_from_associations(self, routes, key):
        """Get ids from associations."""
        return [
            _f.get(key) for _f in sum([_r['Associations'] for _r in routes],
                                      []) if _f.get(key) and not _f.get('Main')
        ]
