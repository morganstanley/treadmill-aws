"""Common AWS command line helpers.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import csv
import collections
import re

import click

from treadmill import cli

from treadmill_aws import awscontext


# Regex matching subnet-id
_SUBNET_ID_RE = r'^subnet-[0-9a-fA-F]+$'

# Regex matching security-group-id
_SECURITY_GROUP_ID_RE = r'^sg-[0-9a-fA-F]+$'

# Regex matching ami-id
_AMI_ID_RE = r'^ami-[0-9a-fA-F]+$'

# Regex matching vpc-id
_VPC_ID_RE = r'^vpc-[0-9a-fA-F]+$'

# Regex matching instance-id
_INSTANCE_ID_RE = r'^i-[0-9a-fA-F]+$'

# Regex matching key=value tags.
_TAGS_RE = r'^([^=]+=[^=]+)(,[^=]+=[^=]+)*$'


def handle_context_opt(ctx, param, value):
    """Handle eager CLI options to configure context.

    The eager options are evaluated directly during parsing phase, and can
    affect other options parsing (like required/not).

    The only side effect of consuming these options are setting attributes
    of the global context.
    """

    if not value or ctx.resilient_parsing:
        return None

    if value == '-':
        return None

    opt = param.name
    if opt == 'aws_region':
        awscontext.GLOBAL.region_name = value

    if opt == 'aws_profile':
        awscontext.GLOBAL.aws_profile = value

    if opt == 'ipa_certs':
        awscontext.GLOBAL.ipa_certs = value

    if opt == 'ipa_domain':
        awscontext.GLOBAL.ipa_domain = value

    return value


# Suppress pylint warnings concerning unused Click arguments
# pylint: disable=W0613
def convert_disk_size_to_int(ctx, param, value):
    """Convert friendly cli option to int
    """
    if isinstance(value, int):
        if value > 0:
            return value
        else:
            raise ValueError('Disk must be greater than 0 GB')

    size = re.search(r'\d+', value)
    if size:
        return int(size.group())
    else:
        raise ValueError("Can't interpret %r" % value)


class _Resource(click.ParamType):
    """Custom input type AWS resources."""

    def __init__(self, regex_id):
        self.regex_id = regex_id
        super().__init__()

    def convert(self, value, param, ctx):
        """Convert command line argument to AWS resource selector."""
        if not value or ctx.resilient_parsing:
            return {}

        if value == '-':
            return {}

        arg = {'tags': collections.defaultdict(list)}
        for line in csv.reader([value]):
            for item in line:
                if re.match(self.regex_id, item):
                    arg['ids'] = [item]
                elif re.match(_TAGS_RE, item):
                    tag_name, tag_value = item.split('=', 1)
                    arg['tags'][tag_name].append(tag_value)
                else:
                    self._handle_default(arg, value)

        arg['tags'] = dict(arg['tags'])
        return arg

    def _handle_default(self, arg, value):
        """Handle value that does not match tag or id pattern."""
        arg['tags']['Name'] = value


class _Subnet(_Resource):
    """CLI Subnet type."""
    name = "subnet"

    def __init__(self):
        super().__init__(_SUBNET_ID_RE)


class _SecurityGroup(_Resource):
    """CLI security group type."""
    name = "secgroup"

    def __init__(self):
        super().__init__(_SECURITY_GROUP_ID_RE)


class _Vpc(_Resource):
    """CLI vpc type."""
    name = "vpc"

    def __init__(self):
        super().__init__(_VPC_ID_RE)


class _Image(_Resource):
    """CLI image type."""
    name = "image"

    def __init__(self):
        super().__init__(_AMI_ID_RE)

    def _handle_default(self, arg, value):
        """Handle value that does not match tag or id pattern."""
        arg['name'] = value


class _Instance(_Resource):
    """CLI instance type."""
    name = "instance"

    def __init__(self):
        super().__init__(_INSTANCE_ID_RE)

    def _handle_default(self, arg, value):
        """Handle value that does not match tag or id pattern."""
        arg['hostnames'] = [value]


SUBNET = _Subnet()

SECGROUP = _SecurityGroup()

IMAGE = _Image()

VPC = _Vpc()

INSTANCE = _Instance()
