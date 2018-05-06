"""Implementation of treadmill admin EC2 CLI plugin.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import botocore
import click

from treadmill import cli

import treadmill_aws
from treadmill_aws import awscontext


def init():
    """Return top level command handler"""

    @click.group(cls=cli.make_commands(__name__))
    def aws():
        """Manage AWS"""
        pass

    return aws
