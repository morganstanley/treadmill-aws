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

EC2_EXCEPTIONS = [
    (botocore.errorfactory.ClientError, None),
]


ON_EC2_EXCEPTIONS = cli.handle_cli_exceptions(EC2_EXCEPTIONS)


def init():
    """Return top level command handler"""

    @click.group(cls=cli.make_commands(__name__))
    @click.option('--aws-region', required=False,
                  envvar='AWS_REGION',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    @click.option('--ipa-domain', required=False,
                  envvar='IPA_DOMAIN',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    @click.option('--ipa-certs', required=False,
                  default='/etc/ipa/ca.crt',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    def ec2():
        """Manage EC2"""
        pass

    return ec2
