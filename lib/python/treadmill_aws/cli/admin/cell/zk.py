"""Admin module to manage cell ZooKeeper servers.
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
from treadmill import exc

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import hostmanager


_LOGGER = logging.getLogger(__name__)


def init():
    """Admin Cell CLI module"""

    @click.group(name='zk')
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
    @click.option('--ipa-certs', required=False,
                  default='/etc/ipa/ca.crt',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    @click.option('--ipa-domain', required=False,
                  envvar='IPA_DOMAIN',
                  callback=treadmill_aws.cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    def zk_grp():
        """Manage cell ZooKeeper servers."""

    @click.option('--cell', required=True, envvar='TREADMILL_CELL')
    @click.option('--hostname', help='Hostname to create')
    @click.option('--instance-profile', help='EC2 instance profile')
    @click.option('--instance-type', help='EC2 instance type')
    @click.option('--subnet', help='Subnet')
    @click.option('--image', help='Image')
    @click.option('--disk', help='Disk size (G)')
    @zk_grp.command(name='create')
    def create_cmd(cell, hostname, instance_profile, instance_type, subnet,
                   image, disk):
        """Create cell ZooKeeper server(s)."""
        ec2_conn = awscontext.GLOBAL.ec2
        ipa_client = awscontext.GLOBAL.ipaclient

        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        masters = admin_cell.get(cell, dirty=True)['masters']

        if hostname:
            masters = [
                master for master in masters if master['hostname'] == hostname
            ]
            if not masters:
                cli.bad_exit('%s not found in the cell config', hostname)

        for master in masters:
            try:
                ec2_instance = ec2client.get_instance(
                    ec2_conn, hostnames=[master['hostname']]
                )
                cli.out('%s EC2 instance already exists', master['hostname'])
                _LOGGER.debug(ec2_instance)
            except exc.NotFoundError:
                hostmanager.create_zk(
                    ec2_conn=ec2_conn,
                    ipa_client=ipa_client,
                    master=master,
                    subnet_id=subnet,
                    instance_type=instance_type,
                    instance_profile=instance_profile,
                    image_id=image,
                    disk=disk
                )
                cli.out('Created: %s', master['hostname'])

    @click.option('--cell', required=True, envvar='TREADMILL_CELL')
    @click.option('--hostname', help='Hostname to rotate', required=True)
    @click.option('--instance-profile', help='EC2 instance profile')
    @click.option('--instance-type', help='EC2 instance type')
    @click.option('--subnet', help='Subnet')
    @click.option('--image', help='Image')
    @click.option('--disk', help='Disk size (G)')
    @zk_grp.command(name='rotate')
    def rotate_cmd(cell, hostname, instance_profile, instance_type, subnet,
                   image, disk):
        """Rotate cell ZooKeeper server."""
        ec2_conn = awscontext.GLOBAL.ec2
        ipa_client = awscontext.GLOBAL.ipaclient

        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        masters = admin_cell.get(cell, dirty=True)['masters']

        try:
            master = next(
                master for master in masters if master['hostname'] == hostname
            )
        except StopIteration:
            cli.bad_exit('%s not found in the cell config', hostname)

        try:
            ec2_instance = ec2client.get_instance(
                ec2_conn, hostnames=[hostname]
            )
            _LOGGER.debug(ec2_instance)
        except exc.NotFoundError:
            cli.bad_exit('%s EC2 instance does not exist', hostname)

        hostmanager.delete_hosts(ec2_conn, ipa_client, [hostname])
        cli.out('Deleted: %s', hostname)

        # Copy subnet, type and image from the old instance unless we override.
        hostmanager.create_zk(
            ec2_conn=ec2_conn,
            ipa_client=ipa_client,
            master=master,
            subnet_id=subnet or ec2_instance['SubnetId'],
            instance_type=instance_type or ec2_instance['InstanceType'],
            instance_profile=instance_profile,
            image_id=image or ec2_instance['ImageId'],
            disk=disk
        )
        cli.out('Created: %s', hostname)

    del create_cmd
    del rotate_cmd

    return zk_grp
