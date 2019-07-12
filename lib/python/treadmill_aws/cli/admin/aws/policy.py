"""Implementation of treadmill admin aws policy.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import re

import click

from treadmill import cli
from treadmill_aws import awscontext

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


class IamPolicy(click.ParamType):
    """IAMPolicy ParamType"""
    name = 'policy-arn'

    def convert(self, value, param, ctx):
        sts = awscontext.GLOBAL.sts
        accountid = sts.get_caller_identity().get('Account')
        pattern = r'^local:(.*)$'
        match = re.search(pattern, value)
        if match:
            return "arn:aws:iam::%s:policy/%s" % (accountid, match.group(1))
        pattern = r'^global:(.*)$'
        match = re.search(pattern, value)
        if match:
            return "arn:aws:iam:::policy/%s" % match.group(1)
        pattern = r'^arn:aws:iam:(.*)$'
        match = re.search(pattern, value)
        if match:
            return value

        self.fail('[%s] invalid syntax, must be of form [local:policy-name, '
                  'global:policy-name, policy-arn]' % value)

        return None


def init():
    """Manage IAM policies."""

    formatter = cli.make_formatter('aws_policy')

    @click.group()
    def policy():
        """Manage IAM policies."""
        pass

    @policy.command()
    @click.option('--version-id',
                  help='Version ID of policy')
    @click.argument('policy', type=IamPolicy())
    @cli.admin.ON_EXCEPTIONS
    def configure(policy, version_id):
        """configure/get IAM policy."""

        iam_conn = awscontext.GLOBAL.iam
        response = iam_conn.get_policy(PolicyArn=policy)
        if not version_id:
            version_id = response['Policy']['DefaultVersionId']
        version = iam_conn.get_policy_version(PolicyArn=policy,
                                              VersionId=version_id)
        response['Policy']['PolicyVersion'] = version['PolicyVersion']
        cli.out(formatter(response['Policy']))

    del configure

    return policy
