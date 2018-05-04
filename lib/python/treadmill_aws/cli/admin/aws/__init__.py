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

AWS_EXCEPTIONS = [
    (botocore.errorfactory.ClientError, None),
]

try:
    ON_AWS_EXCEPTIONS = cli.handle_cli_exceptions(AWS_EXCEPTIONS)
except:
    # TODO: depends which version of treadmill is used, the signature changed.
    #       until versions in github and internal are reconciled, need to use
    #       this hack.
    ON_AWS_EXCEPTIONS = cli.handle_exceptions(AWS_EXCEPTIONS)


def init():
    """Return top level command handler"""

    @click.group(cls=cli.make_commands(__name__))
    @click.option('--aws-region', required=False,
                  envvar='AWS_REGION',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    @click.option('--aws-profile', required=False,
                  envvar='AWS_PROFILE',
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
    def aws():
        """Manage AWS"""
        pass

    return aws
