"""Table CLI formatter.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import yaml

from treadmill.formatter import tablefmt
from treadmill import yamlwrapper as yaml


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
        def _hostname_from_tags(tags):
            """Get hostname from tags."""
            for tag in tags:
                if tag['Key'] == 'Name':
                    return tag['Value']
            return None

        item_schema = [
            ('hostname', 'Tags', _hostname_from_tags),
            ('id', 'InstanceId', None),
            ('arch', 'Architecture', None),
            ('image', 'ImageId', None),
            ('type', 'InstanceType', None),
            ('key', 'KeyName', None),
            ('launch', 'LaunchTime', None),
            ('status', 'Status', None),
            ('vpc', 'VpcId', None),
            ('subnet', 'SubnetId', None),
            ('tags', 'Tags', _fmt_tags()),
        ]

        list_schema = [
            ('hostname', 'Tags', _hostname_from_tags),
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


class RolePrettyFormatter:
    """Pretty table formatter for AWS roles."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        list_schema = [
            ('name', 'RoleName', None),
            ('id', 'RoleId', None),
            ('path', 'Path', None),
        ]

        # TODO: add role policy document schema.
        item_schema = list_schema + [
            ('arn', 'Arn', None),
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
    """Pretty table formatter for IPA user."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        list_schema = [
            ('id', 'User', lambda _: _['UserName']),
        ]

        item_schema = [
            ('id', 'user', lambda _: _['UserName']),
            ('user', 'user', yaml.dump),
            ('role', 'role', yaml.dump),
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
            ('image', 'image', None),
            ('docker-registries', 'docker_registries', ','.join),
            ('size', 'size', None),
            ('disk-size', 'disk_size', None),
            ('hostgroups', 'hostgroups', ','.join),
            ('secgroup', 'secgroup', None),
            ('realm', 'realm', None),
            ('instance-profile', 'instance_profile', None),
            ('subnets', 'subnets', ','.join),
        ]

        format_item = tablefmt.make_dict_to_table(schema)
        format_list = tablefmt.make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)
