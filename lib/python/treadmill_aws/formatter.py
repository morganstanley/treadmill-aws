"""Table CLI formatter.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from treadmill.formatter import tablefmt


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


class SubnetPrettyFormatter(object):
    """Pretty table formatter for EC2 subnets."""

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


class VpcPrettyFormatter(object):
    """Pretty table formatter for EC2 vpcs."""

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


class InstancePrettyFormatter(object):
    """Pretty table formatter for EC2 instances."""

    @staticmethod
    def format(item):
        """Return pretty-formatted item."""
        def _hostname_from_tags(tags):
            """Get hostname from tags."""
            for tag in tags:
                if tag['Key'] == 'Name':
                    return tag['Value']
            return None

        schema = [
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

        format_item = tablefmt.make_dict_to_table(schema)
        format_list = tablefmt.make_list_to_table(schema)

        if isinstance(item, list):
            return format_list(item)
        else:
            return format_item(item)