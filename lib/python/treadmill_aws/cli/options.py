"""Helpers to construct options handler for AWS resources."""

import collections
import csv
import re


# Regex matching subnet-id
_SUBNET_ID_RE = r'^subnet-[0-9a-fA-F]+$'

# Regex matching subnet-id
_SECURITY_GROUP_ID_RE = r'^sg-[0-9a-fA-F]+$'

# Regex matching subnet-id
_AMI_ID_RE = r'^ami-[0-9a-fA-F]+$'

# Regex matching key=value tags.
_TAGS_RE = r'^([^=]+=[^=]+)(,[^=]+=[^=]+)*$'


def parse(regex_id, default=None):
    """Parse argument given entity id regex."""

    def _default_handler(arg, value):
        """Default handler, add to the name tag."""
        arg['tags']['Name'].append(value)

    if not default:
        default = _default_handler

    def _handle_opt(ctx, _param, value):
        """Handle subnet options."""
        if not value or ctx.resilient_parsing:
            return {}

        if value == '-':
            return {}

        arg = {'tags': collections.defaultdict(list)}

        for line in csv.reader([value]):
            for item in line:
                if re.match(regex_id, item):
                    arg['id'] = item
                elif re.match(_TAGS_RE, item):
                    tag_name, tag_value = item.split('=', 1)
                    arg['tags'][tag_name].append(tag_value)
                else:
                    if default:
                        default(arg, value)

        arg['tags'] = dict(arg['tags'])
        return arg

    return _handle_opt


def parse_subnet():
    """Parse subnet CLI options."""
    return parse(_SUBNET_ID_RE)


def parse_security_group():
    """Parse subnet CLI options."""
    return parse(_SECURITY_GROUP_ID_RE)


def parse_image():
    """Parse image CLI options."""
    def _default_handler(arg, value):
        """Handle default argument for image, storing name."""
        arg['name'] = value

    return parse(_AMI_ID_RE, default=_default_handler)
