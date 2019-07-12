"""Implementation of treadmill admin aws role.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import io
import json
import logging

import click

from treadmill import cli
from treadmill import exc

from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli
from treadmill_aws import iamclient

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


def _generate_trust_document(trust_root,
                             trusted_users,
                             trusted_services,
                             trusted_saml_providers):
    """Default role policy."""

    account = awscontext.GLOBAL.sts.get_caller_identity().get('Account')

    statements = []
    if trust_root or trusted_users or trusted_services:

        trusted_principals = {}
        trusted_aws_principals = []

        if trust_root:
            trusted_aws_principals.append(
                'arn:aws:iam::{}:root'.format(account))

        if trusted_users:
            for user in trusted_users:
                trusted_aws_principals.append(
                    'arn:aws:iam::{}:user/{}'.format(account, user))

        if trusted_aws_principals:
            trusted_principals['AWS'] = trusted_aws_principals

        if trusted_services:
            trusted_principals['Service'] = trusted_services

        statement = {
            'Action': 'sts:AssumeRole',
            'Effect': 'Allow',
            'Principal': trusted_principals
        }
        statements.append(statement)

    if trusted_saml_providers:
        principals = []
        for saml_provider in trusted_saml_providers:
            pol = 'arn:aws:iam::%s:saml-provider/%s' % (account, saml_provider)
            principals.append(pol)

        statement = {
            'Action': 'sts:AssumeRoleWithSAML',
            'Effect': 'Allow',
            'Principal': {
                'Federated': principals
            },
            'Condition': {
                'StringEquals': {
                    'SAML:aud': 'https://signin.aws.amazon.com/saml'
                }
            }
        }
        statements.append(statement)

    if statements:
        policy = {}
        policy['Version'] = '2012-10-17'
        policy['Statement'] = statements
        return json.dumps(policy)

    return None


def _set_role_policies(iam_conn, role_name, role_policies):
    new_pols = []

    if role_policies == [':']:
        role_policies = []

    for pol in role_policies:
        policy_name, policy_file = pol.split(':', 2)
        new_pols.append(policy_name)
        with io.open(policy_file) as f:
            policy_document = f.read()
        _LOGGER.info('set/updated inline policy: %s', policy_name)
        iamclient.put_role_policy(iam_conn,
                                  role_name,
                                  policy_name,
                                  policy_document)
    all_pols = iamclient.list_role_policies(iam_conn, role_name)
    for policy_name in all_pols:
        if policy_name not in new_pols:
            _LOGGER.info('removing inline policy: %s', policy_name)
            iamclient.delete_role_policy(iam_conn,
                                         role_name,
                                         policy_name)


def _set_attached_policies(iam_conn, role_name, attached_policies):
    sts = awscontext.GLOBAL.sts
    accountid = sts.get_caller_identity().get('Account')

    if attached_policies == [':']:
        attached_policies = []

    del_pols = {}
    for policy in iamclient.list_attached_role_policies(iam_conn,
                                                        role_name):
        del_pols[policy['PolicyArn']] = 1

    new_pols = {}
    for policy in attached_policies:
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
            iamclient.detach_role_policy(iam_conn,
                                         role_name,
                                         policy_arn)
        else:
            del new_pols[policy_arn]

    for policy_arn in new_pols:
        _LOGGER.info('attaching policy: %s', policy_arn)
        iamclient.attach_role_policy(iam_conn, role_name, policy_arn)


def _create_role(iam_conn,
                 role_name,
                 path,
                 trust_document,
                 max_session_duration):
    if not max_session_duration:
        max_session_duration = 43200
    iamclient.create_role(iam_conn,
                          role_name,
                          path,
                          trust_document,
                          max_session_duration)


# pylint: disable=R0915
def init():
    """Manage IAM roles."""

    formatter = cli.make_formatter('aws_role')

    @click.group()
    def role():
        """Manage IAM roles."""
        pass

    @role.command()
    @click.option('--create',
                  is_flag=True,
                  default=False,
                  help='Create if it does not exist')
    @click.option('--path',
                  default='/',
                  help='Path for user name.')
    @click.option('--max-session-duration',
                  type=click.IntRange(3600, 43200),
                  required=False,
                  help='maximum session duration.')
    @click.option('--trust-policy',
                  required=False,
                  help='Trust policy (aka assume role policy).')
    @click.option('--trust-root',
                  is_flag=True,
                  default=False,
                  help='Allow root to assume role')
    @click.option('--trusted-users',
                  type=cli.LIST,
                  required=False,
                  help='IAM users allowed to assume role')
    @click.option('--trusted-saml-providers',
                  type=cli.LIST,
                  required=False,
                  help='Trusted SAML Providers')
    @click.option('--trusted-services',
                  type=cli.LIST,
                  required=False,
                  help='AWS services allowed to assume role, e.g., '
                       'ec2.amazonaws.com')
    @click.option('--inline-policies',
                  type=cli.LIST,
                  required=False,
                  help='Inline role policies, list of '
                       '<RolePolicyName>:<file>')
    @click.option('--attached-policies',
                  type=cli.LIST,
                  required=False,
                  help='Attached policies, list of '
                       'global:<PolicyName> or local:<PolicyName>')
    @click.argument('role_name',
                    required=True,
                    callback=aws_cli.sanitize_user_name)
    @cli.admin.ON_EXCEPTIONS
    def configure(create,
                  path,
                  max_session_duration,
                  trust_policy,
                  trust_root,
                  trusted_users,
                  trusted_services,
                  trusted_saml_providers,
                  inline_policies,
                  attached_policies,
                  role_name):
        """Create/configure/get IAM role."""

        iam_conn = awscontext.GLOBAL.iam

        try:
            role = iamclient.get_role(iam_conn, role_name)
        except exc.NotFoundError:
            if not create:
                raise
            role = None

        if trust_policy:
            with io.open(trust_policy) as f:
                trust_document = f.read()
        elif (trust_root or
              trusted_users or
              trusted_services or
              trusted_saml_providers):
            trust_document = _generate_trust_document(trust_root,
                                                      trusted_users,
                                                      trusted_services,
                                                      trusted_saml_providers)
        elif create:
            raise click.UsageError('Must specify one of the following:\n'
                                   '  --trust-policy\n'
                                   '  --trust-root\n'
                                   '  --trusted-user\n'
                                   '  --trusted-service\n'
                                   '  --trusted-saml-provider')
        else:
            trust_document = None

        if not role:
            _create_role(iam_conn,
                         role_name,
                         path,
                         trust_document,
                         max_session_duration)
        else:
            if max_session_duration:
                iamclient.update_role(iam_conn,
                                      role_name,
                                      max_session_duration)
            if trust_document:
                iamclient.update_assume_role_policy(iam_conn,
                                                    role_name,
                                                    trust_document)

        if inline_policies:
            _set_role_policies(iam_conn, role_name, inline_policies)

        if attached_policies:
            _set_attached_policies(iam_conn, role_name, attached_policies)

        role = iamclient.get_role(iam_conn, role_name)
        role['RolePolicies'] = iamclient.list_role_policies(iam_conn,
                                                            role_name)
        role['AttachedPolicies'] = iamclient.list_attached_role_policies(
            iam_conn,
            role_name)
        cli.out(formatter(role))

    @role.command(name='list')
    @click.option('--path',
                  default='/',
                  help='Path for user name.')
    @cli.admin.ON_EXCEPTIONS
    def list_roles(path):
        """List IAM roles.
        """

        iam_conn = awscontext.GLOBAL.iam
        roles = iamclient.list_roles(iam_conn, path)
        cli.out(formatter(roles))

    @role.command()
    @click.option('--force',
                  is_flag=True,
                  default=False,
                  help='Delete role, even is role has policies attached.')
    @click.argument('role-name')
    @cli.admin.ON_EXCEPTIONS
    def delete(force, role_name):
        """Delete IAM role."""
        iam_conn = awscontext.GLOBAL.iam
        if force:
            role_policies = iamclient.list_role_policies(iam_conn, role_name)
            for policy in role_policies:
                _LOGGER.info('deleting inline policy: %s', policy)
                iamclient.delete_role_policy(iam_conn, role_name, policy)

            attached_pols = iamclient.list_attached_role_policies(iam_conn,
                                                                  role_name)
            for policy in attached_pols:
                _LOGGER.info('detaching policy: %s', policy['PolicyArn'])
                iamclient.detach_role_policy(iam_conn,
                                             role_name,
                                             policy['PolicyArn'])

        try:
            iamclient.delete_role(iam_conn, role_name)
        except iam_conn.exceptions.DeleteConflictException:
            raise click.UsageError('Role [%s] has inline or attached policies,'
                                   'use --force to force delete.' % role_name)

    del configure
    del delete
    return role
