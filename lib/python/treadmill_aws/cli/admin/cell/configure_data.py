"""Admin module to manage cell data.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill import admin
from treadmill import context
from treadmill import cli


_LOGGER = logging.getLogger(__name__)


def _set(data, name, value, unset_value=None):
    """Safely set data attribute or unset if user set it to a special value."""
    if value is None:
        return False

    if unset_value is not None and value == unset_value:
        data.pop(name, None)
    elif value in ('-', ['-']):
        data.pop(name, None)
    else:
        data[name] = value
    return True


def init():
    """Admin Cell CLI module"""

    formatter = cli.make_formatter('aws_cell_data')

    @click.command(name='configure-data')
    @click.option('--aws-account', help='AWS account.')
    @click.option('--aws-admin', help='AWS privileged user.')
    @click.option('--aws-region', help='AWS region.')
    # TODO: support XXXG as input.
    @click.option('--disk-size', help='Default image disk size.')
    @click.option('--docker-registries', help='Docker registries',
                  type=cli.LIST)
    @click.option('--hostgroups', help='Nodes hostgroups.', type=cli.LIST)
    @click.option('--image', help='Default AMI image.')
    @click.option('--image-accounts',
                  help='AMI source accounts',
                  type=cli.LIST)
    # TODO: should be list.
    @click.option('--instance-profile', help='Instance profile.')
    @click.option('--realm', help='Nodes kerberos realm.')
    @click.option('--s3-registry-bucket', help='S3 registry bucket name.')
    @click.option('--secgroup', help='Nodes security group.')
    @click.option('--size', help='Default instance size.')
    @click.option('--sns-topic', help='SNS alert topic')
    @click.option('--subnets', help='List of subnets.', type=cli.LIST)
    @click.option('--tls-ca-cert', help='CA Cert Path')
    @click.option('--tls-host-cert', help='Host Cert Path')
    @click.option('--tls-host-key', help='Host Key Path')
    def configure_data_cmd(aws_account,
                           aws_admin,
                           aws_region,
                           disk_size,
                           docker_registries,
                           hostgroups,
                           image,
                           image_accounts,
                           instance_profile,
                           realm,
                           secgroup,
                           size,
                           sns_topic,
                           subnets,
                           s3_registry_bucket,
                           tls_ca_cert,
                           tls_host_cert,
                           tls_host_key):
        """Configure cell data."""
        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(context.GLOBAL.cell)
        data = cell.get('data', {})

        tls_certs = data.get('tls_certs', {})
        _set(tls_certs, 'ca_cert', tls_ca_cert)
        _set(tls_certs, 'host_cert', tls_host_cert)
        _set(tls_certs, 'host_key', tls_host_key)
        if not any(tls_certs.values()):
            tls_certs = '-'

        modified = _set(data, 'aws_account', aws_account)
        modified = _set(data, 'aws_admin', aws_admin) or modified
        modified = _set(data, 'aws_region', aws_region) or modified
        modified = _set(data,
                        'docker_registries',
                        docker_registries) or modified
        modified = _set(data, 'disk_size', disk_size) or modified
        modified = _set(data, 'hostgroups', hostgroups) or modified
        modified = _set(data, 'image', image) or modified
        modified = _set(data, 'image_accounts', image_accounts) or modified
        modified = _set(data, 'instance_profile', instance_profile) or modified
        modified = _set(data, 'realm', realm) or modified
        modified = _set(data, 'secgroup', secgroup) or modified
        modified = _set(data, 'size', size) or modified
        modified = _set(data, 'sns_topic', sns_topic) or modified
        modified = _set(data, 'subnets', subnets) or modified
        modified = _set(data,
                        's3_registry_bucket',
                        s3_registry_bucket) or modified
        modified = _set(data,
                        'tls_certs',
                        tls_certs,
                        unset_value={}) or modified

        if modified:
            admin_cell.update(context.GLOBAL.cell, {'data': data})
        cli.out(formatter(data))

    return configure_data_cmd
