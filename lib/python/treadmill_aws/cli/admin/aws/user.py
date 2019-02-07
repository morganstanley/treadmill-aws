"""Implementation of treadmill admin AWS user manager.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import logging

import click

from treadmill import cli
from treadmill import exc

from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli
from treadmill_aws import iamclient

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


def _set_user_policy(iam_conn, user_name, user_policy):
    new_pols = []

    if user_policy == [':']:
        user_policy = []

    for pol in user_policy:
        policy_name, policy_file = pol.split(':', 2)
        new_pols.append(policy_name)
        with io.open(policy_file) as f:
            policy_document = f.read()
        _LOGGER.info('set/updated inline policy: %s', policy_name)
        iamclient.put_user_policy(iam_conn,
                                  user_name,
                                  policy_name,
                                  policy_document)
    all_pols = iamclient.list_user_policies(iam_conn, user_name)
    for policy_name in all_pols:
        if policy_name not in new_pols:
            _LOGGER.info('removing inline policy: %s', policy_name)
            iamclient.delete_user_policy(iam_conn,
                                         user_name,
                                         policy_name)


def _set_attached_policy(iam_conn, user_name, attached_policy):
    sts = awscontext.GLOBAL.sts
    accountid = sts.get_caller_identity().get('Account')

    if attached_policy == [':']:
        attached_policy = []

    del_pols = {}
    for policy in iamclient.list_attached_user_policies(iam_conn,
                                                        user_name):
        del_pols[policy['PolicyArn']] = 1

    new_pols = {}
    for policy in attached_policy:
        scope, policy_name = policy.split(':', 2)
        if scope == 'global':
            new_pols['arn:aws:iam::aws:policy/%s' % policy_name] = 1
        elif scope == 'local':
            pol = 'arn:aws:iam::%s:policy/%s' % (accountid, policy_name)
            new_pols[pol] = 1
        else:
            raise click.UsageError('Invalid policy scope [%s]' % scope)

    for policy_arn in del_pols:
        if policy_arn not in new_pols:
            _LOGGER.info('detaching policy: %s', policy_arn)
            iamclient.detach_user_policy(iam_conn,
                                         user_name,
                                         policy_arn)
        else:
            del new_pols[policy_arn]

    for policy_arn in new_pols:
        _LOGGER.info('attaching policy: %s', policy_arn)
        iamclient.attach_user_policy(iam_conn, user_name, policy_arn)


def init():
    """Manage IAM users."""

    formatter = cli.make_formatter('aws_user')

    @click.group()
    def user():
        """Manage IAM users."""
        pass

    @user.command()
    @click.option('--create',
                  is_flag=True,
                  default=False,
                  help='Create if it does not exist')
    @click.option('--path',
                  default='/',
                  help='Path for user name.')
    @click.option('--inline-policy',
                  type=cli.LIST,
                  required=False,
                  help='Inline user policy name:file')
    @click.option('--attached-policy',
                  type=cli.LIST,
                  required=False,
                  help='global:PolicyName or local:PolicyName')
    @click.option('--attached-policy',
                  type=cli.LIST,
                  required=False,
                  help='global:PolicyName or local:PolicyName')
    @click.argument('user-name',
                    required=True,
                    callback=aws_cli.sanitize_user_name)
    @cli.admin.ON_EXCEPTIONS
    def configure(create,
                  path,
                  inline_policy,
                  attached_policy,
                  user_name):
        """Create/configure/get IAM user."""

        iam_conn = awscontext.GLOBAL.iam

        try:
            user = iamclient.get_user(iam_conn, user_name)
        except exc.NotFoundError:
            if not create:
                raise
            user = None

        if not user:
            user = iamclient.create_user(iam_conn, user_name, path)

        if inline_policy:
            _set_user_policy(iam_conn, user_name, inline_policy)

        if attached_policy:
            _set_attached_policy(iam_conn, user_name, attached_policy)

        user['UserPolicies'] = iamclient.list_user_policies(iam_conn,
                                                            user_name)
        user['AttachedPolicies'] = iamclient.list_attached_user_policies(
            iam_conn,
            user_name)
        cli.out(formatter(user))

    @user.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    @click.option('--path',
                  default='/',
                  help='Path for user name.')
    def list_users(path):
        """List IAM users.
        """
        iam_conn = awscontext.GLOBAL.iam
        users = iamclient.list_users(iam_conn, path)
        cli.out(formatter(users))

    @user.command()
    @click.option('--force',
                  is_flag=True,
                  default=False,
                  help='Delete user, even is user has policies attached.')
    @click.argument('user-name')
    @cli.admin.ON_EXCEPTIONS
    def delete(force, user_name):
        """Delete IAM user."""
        iam_conn = awscontext.GLOBAL.iam

        if force:
            user_policies = iamclient.list_user_policies(iam_conn,
                                                         user_name)
            for policy in user_policies:
                _LOGGER.info('deleting inline policy: %s', policy)
                iamclient.delete_user_policy(iam_conn, user_name, policy)

            attached_pols = iamclient.list_attached_user_policies(iam_conn,
                                                                  user_name)
            for policy in attached_pols:
                _LOGGER.info('detaching policy: %s', policy['PolicyArn'])
                iamclient.detach_user_policy(iam_conn,
                                             user_name,
                                             policy['PolicyArn'])

            groups = iamclient.list_groups_for_user(iam_conn,
                                                    user_name)
            for group in groups:
                _LOGGER.info('removing user from group: %s', group)
                iamclient.remove_user_from_group(iam_conn,
                                                 user_name,
                                                 group)

        try:
            iamclient.delete_user(iam_conn=iam_conn, user_name=user_name)
        except iam_conn.exceptions.DeleteConflictException:
            raise click.UsageError('User [%s] has inline or attached '
                                   'policies, or is a member of one or '
                                   'more group, use --force to force '
                                   'delete.' % user_name)

    del configure
    del list_users
    del delete

    return user
