"""Table CLI formatter.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from treadmill.formatter import tablefmt


def _state(state):
    """Get status from instance."""
    return state['Name']


def _name_from_tags(tags):
    """Get name from tags."""
    for tag in tags:
        if tag['Key'] == 'Name':
            return tag['Value']
    return None


def _fmt_tags():
    """Output formatter tags."""

    def _fmt(items):
        """Format tags, discard cloudformation tags."""
        filtered = [
            item for item in items
            if not item['Key'].startswith('aws:cloudformation:')
        ]
        schema = [
            ('key', 'Key', None),
            ('value', 'Value', None),
        ]
        return tablefmt.list_to_table(
            filtered, schema, header=False, align=None
        )

    return _fmt


def _fmt_secgroups():
    """Output formatter security groups."""

    def _fmt(items):
        """Format tags, discard cloudformation tags."""
        schema = [
            ('name', 'GroupName', None),
            ('id', 'GroupId', None),
        ]
        return tablefmt.list_to_table(
            items, schema, header=False, align=None
        )

    return _fmt


def _fmt_list():
    """Output formatter list."""

    def _fmt(items):
        """Format list."""
        schema = [
            ('item', None, None),
        ]
        return tablefmt.list_to_table(
            items, schema, header=False, align=None
        )

    return _fmt


def _fmt_trusted_entities(policy):

    def _root_is_trusted(statement):
        return bool((statement['Action'] == 'sts:AssumeRole' and
                     statement['Effect'] == 'Allow' and
                     'AWS' in statement['Principal']))

    def _service_is_trusted(statement):
        return bool((statement['Action'] == 'sts:AssumeRole' and
                     statement['Effect'] == 'Allow' and
                     'Service' in statement['Principal']))

    def _saml_is_trusted(statement):
        return bool((statement['Action'] == 'sts:AssumeRoleWithSAML' and
                     statement['Effect'] == 'Allow'))

    def _trusted_entities(pol):
        entities = []
        for statement in pol['Statement']:
            if _root_is_trusted(statement):
                entities.append({'Type': 'Account',
                                 'Entity': statement['Principal']['AWS']})
            if _service_is_trusted(statement):
                entities.append({'Type': 'Service',
                                 'Entity': statement['Principal']['Service']})
            if _saml_is_trusted(statement):
                if 'Federated' in statement['Principal']:
                    princ_list = statement['Principal']['Federated']
                    if isinstance(princ_list, str):
                        entities.append({'Type': 'SAMLProvider',
                                         'Entity': princ_list})
                    else:
                        princ_list.sort()
                        for principal in princ_list:
                            entities.append({'Type': 'SAMLProvider',
                                             'Entity': principal})
        return entities

    items = _trusted_entities(policy)

    schema = [
        ('Type', 'Type', None),
        ('Entity', 'Entity', None)
    ]
    return tablefmt.list_to_table(items, schema, header=False, align=None)


def _fmt_attached_policies(policies):
    def _fpolicies(policies):
        fpolicies = []
        for policy in policies:
            if policy['PolicyArn']. startswith('arn:aws:iam::aws:policy/'):
                pn = policy['PolicyArn'].replace('arn:aws:iam::aws:policy/',
                                                 '')
                fpolicies.append({
                    'Type': 'global',
                    'PolicyName': pn,
                    'PolicyArn': policy['PolicyArn']
                })
            else:
                fpolicies.append({
                    'Type': 'local',
                    'PolicyName': policy['PolicyName'],
                    'PolicyArn': policy['PolicyArn']
                })
        return fpolicies

    items = _fpolicies(policies)
    schema = [
        ('Type', 'Type', None),
        ('PolicyName', 'PolicyName', None),
        ('PolicyArn', 'PolicyArn', None),
    ]
    return tablefmt.list_to_table(items,
                                  schema,
                                  header=False,
                                  align=None,
                                  sortby='PolicyName')


class SubnetPrettyFormatter:
    """Pretty table formatter for AWS subnets."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('id', 'SubnetId', None),
            ('state', 'State', None),
            ('zone', 'AvailabilityZone', None),
            ('cidr_block', 'CidrBlock', None),
            ('vpc', 'VpcId', None),
            ('tags', 'Tags', _fmt_tags()),
        ]

        format_item = tablefmt.make_dict_to_table(schema)
        format_list = tablefmt.make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class VpcPrettyFormatter:
    """Pretty table formatter for AWS vpcs."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('id', 'VpcId', None),
            ('default', 'IsDefault', None),
            ('state', 'State', None),
            ('cidr_block', 'CidrBlock', None),
            ('tags', 'Tags', _fmt_tags()),
        ]

        format_item = tablefmt.make_dict_to_table(schema)
        format_list = tablefmt.make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class InstancePrettyFormatter:
    """Pretty table formatter for AWS instances."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        item_schema = [
            ('hostname', 'Tags', _name_from_tags),
            ('id', 'InstanceId', None),
            ('arch', 'Architecture', None),
            ('image', 'ImageId', None),
            ('type', 'InstanceType', None),
            ('key', 'KeyName', None),
            ('launch', 'LaunchTime', None),
            ('state', 'State', _state),
            ('vpc', 'VpcId', None),
            ('subnet', 'SubnetId', None),
            ('secgroups', 'SecurityGroups', _fmt_secgroups()),
            ('tags', 'Tags', _fmt_tags()),
        ]

        list_schema = [
            ('hostname', 'Tags', _name_from_tags),
            ('id', 'InstanceId', None),
            ('image', 'ImageId', None),
            ('type', 'InstanceType', None),
            ('key', 'KeyName', None),
            ('vpc', 'VpcId', None),
            ('subnet', 'SubnetId', None),
            ('tags', 'Tags', _fmt_tags()),
        ]

        format_item = tablefmt.make_dict_to_table(item_schema)
        format_list = tablefmt.make_list_to_table(list_schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class SpotPrettyFormatter:
    """Pretty table formatter for Spot Instance Requests."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""

        item_schema = [
            ('id', 'id', None),
            ('status', 'state', None),
            ('code', 'status_code', None),
            ('changed', 'status_timestamp', None),
            ('zone', 'az', None),
            ('subnet', 'subnet', None),
            ('type', 'instance_type', None),
            ('instance_id', 'instance_id', None),
            ('ami_id', 'ami_id', None),
            ('hostname', 'hostname', None),
            ('launch', 'instance_launch', None),
            ('state', 'instance_status', None),
        ]

        list_schema = item_schema

        format_item = tablefmt.make_dict_to_table(item_schema)
        format_list = tablefmt.make_list_to_table(list_schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class RolePrettyFormatter:
    """Pretty table formatter for AWS roles."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""

        list_schema = [
            ('RoleName', 'RoleName', None),
            ('Arn', 'Arn', None),
            ('MaxSessionDuration', 'MaxSessionDuration', None),
            ('CreateDate', 'CreateDate', None),
        ]

        item_schema = [
            ('RoleName', 'RoleName', None),
            ('Path', 'Path', None),
            ('Arn', 'Arn', None),
            ('MaxSessionDuration', 'MaxSessionDuration', None),
            ('CreateDate', 'CreateDate', None),
            ('RoleId', 'RoleId', None),
            ('TrustedEntities',
             'AssumeRolePolicyDocument',
             _fmt_trusted_entities),
            ('InlinePolicies', 'RolePolicies', None),
            ('AttachedPolicies', 'AttachedPolicies', _fmt_attached_policies),
        ]

        format_item = tablefmt.make_dict_to_table(item_schema)
        format_list = tablefmt.make_list_to_table(list_schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class SnapshotPrettyFormatter:
    """Pretty table formatter for AWS snaphots."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""

        list_schema = [
            ('Name', 'Tags', _name_from_tags),
            ('SnapshotId', 'SnapshotId', None),
            ('VolumeId', 'VolumeId', None),
            ('State', 'State', None),
            ('Progress', 'Progress', None),
            ('VolumeSize', 'VolumeSize', None),
            ('StartTime', 'StartTime', None),
            ('Description', 'Description', None),
        ]

        item_schema = [
            ('Name', 'Tags', _name_from_tags),
            ('Description', 'Description', None),
            ('SnapshotId', 'SnapshotId', None),
            ('VolumeId', 'VolumeId', None),
            ('State', 'State', None),
            ('Progress', 'Progress', None),
            ('VolumeSize', 'VolumeSize', None),
            ('StartTime', 'StartTime', None),
            ('Encrypted', 'Encrypted', None),
            ('KmsKeyId', 'KmsKeyId', None),
            ('tags', 'Tags', _fmt_tags()),
        ]

        format_item = tablefmt.make_dict_to_table(item_schema)
        format_list = tablefmt.make_list_to_table(list_schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class ImagePrettyFormatter:
    """Pretty table formatter for AWS images."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        list_schema = [
            ('id', 'ImageId', None),
            ('name', 'Name', None),
            ('owner', 'OwnerId', None),
            ('created', 'CreationDate', None),
            ('public', 'Public', lambda v: 'yes' if v else 'no'),
            ('state', 'State', None),
        ]

        item_schema = list_schema + [
            ('tags', 'Tags', _fmt_tags()),
        ]

        format_item = tablefmt.make_dict_to_table(item_schema)
        format_list = tablefmt.make_list_to_table(list_schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class SecgroupPrettyFormatter:
    """Pretty table formatter for AWS security groups."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        list_schema = [
            ('id', 'GroupId', None),
            ('owner', 'OwnerId', None),
            ('vpc', 'VpcId', None),
            ('tags', 'Tags', _fmt_tags()),
        ]

        # TODO: add ip ingress/egress permissions to the output.
        item_schema = [
            ('id', 'GroupId', None),
            ('owner', 'OwnerId', None),
            ('vpc', 'VpcId', None),
            ('tags', 'Tags', _fmt_tags()),
        ]

        format_item = tablefmt.make_dict_to_table(item_schema)
        format_list = tablefmt.make_list_to_table(list_schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class IpaUserPrettyFormatter:
    """Pretty table formatter for AWS user."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        list_schema = [
            ('id', 'uid', lambda _: _[0]),
        ]

        item_schema = [
            ('id', 'uid', lambda _: _[0]),
            ('type', 'userclass', lambda _: _[0]),
            ('groups', 'memberof_group', '\n'.join),
            ('indirect-groups', 'memberofindirect_group', '\n'.join),
            ('hbac-rule', 'memberofindirect_hbacrule', '\n'.join),
            ('sudo-rule', 'memberofindirect_sudorule', '\n'.join),
        ]

        format_item = tablefmt.make_dict_to_table(item_schema)
        format_list = tablefmt.make_list_to_table(list_schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class AwsUserPrettyFormatter:
    """Pretty table formatter for AWS users."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""

        list_schema = [
            ('UserName', 'UserName', None),
            ('Arn', 'Arn', None),
        ]

        item_schema = [
            ('UserName', 'UserName', None),
            ('Path', 'Path', None),
            ('Arn', 'Arn', None),
            ('CreateDate', 'CreateDate', None),
            ('UserId', 'UserId', None),
            ('InlinePolicies', 'UserPolicies', None),
            ('AttachedPolicies', 'AttachedPolicies', _fmt_attached_policies),
        ]

        format_item = tablefmt.make_dict_to_table(item_schema)
        format_list = tablefmt.make_list_to_table(list_schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class CellDataFormatter:
    """Pretty table formatter for cell data."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('aws_account', 'aws_account', None),
            ('aws_admin', 'aws_admin', None),
            ('aws_region', 'aws_region', None),
            ('docker-registries', 'docker_registries', ','.join),
            ('disk-size', 'disk_size', None),
            ('hostgroups', 'hostgroups', ','.join),
            ('image', 'image', None),
            ('image-accounts', 'image_accounts', ','.join),
            ('instance-profile', 'instance_profile', None),
            ('realm', 'realm', None),
            ('secgroup', 'secgroup', None),
            ('size', 'size', None),
            ('sns-topic', 'sns_topic', None),
            ('subnets', 'subnets', ','.join),
            ('s3_registry_bucket', 's3_registry_bucket', None),
            ('tls_certs', 'tls_certs', None),
        ]

        format_item = tablefmt.make_dict_to_table(schema)
        format_list = tablefmt.make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)


class PartDataFormatter:
    """Pretty table formatter for partition data."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        schema = [
            ('autoscale', 'autoscale', None),
            ('image', 'image', None),
            ('image-accounts', 'image_accounts', ','.join),
            ('instance-types', 'instance_types', ','.join),
            ('spot-instance-types', 'spot_instance_types', ','.join),
            ('disk-size', 'disk_size', None),
            ('hostgroups', 'hostgroups', ','.join),
            ('secgroup', 'secgroup', None),
            ('instance-profile', 'instance_profile', None),
            ('subnets', 'subnets', ','.join),
            ('s3_registry_bucket', 's3_registry_bucket', None),
        ]

        format_item = tablefmt.make_dict_to_table(schema)
        format_list = tablefmt.make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)
