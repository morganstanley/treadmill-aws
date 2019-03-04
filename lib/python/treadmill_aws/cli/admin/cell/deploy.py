"""Admin module to manage cell infrastructure
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

    @click.group(name='deploy')
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
    def deploy_grp():
        """Configure cell infra."""
        pass

    @click.option('--cell', required=True, envvar='TREADMILL_CELL')
    @click.option('--rotate', is_flag=True)
    @click.option('--instance_profile', help='EC2 Instance Profile')
    @deploy_grp.command(name='zk')
    def zk_cmd(cell, instance_profile, rotate):
        """Manage Zookeeper servers"""
        ec2_conn = awscontext.GLOBAL.ec2
        ipa_client = awscontext.GLOBAL.ipaclient

        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        masters = admin_cell.get(cell, dirty=True)['masters']
        ec2_instances = []

        # Check that Zookeepers exist; create if missing
        for master in masters:
            try:
                ec2_instances.append(ec2client.get_instance(
                    ec2_conn, hostnames=[master['hostname']]))
            except exc.NotFoundError:
                cli.out(
                    hostmanager.create_zk(
                        ec2_conn=ec2_conn,
                        instance_profile=instance_profile,
                        ipa_client=ipa_client,
                        master=master))

        if rotate and len(ec2_instances) == len(masters):
            # Refuse to rotate if quorum would be broken
            if len(ec2_instances) < 3:
                cli.out('Not enough healthy Zookeepers to rotate')
                return

            cli.out(hostmanager.rotate_zk(ec2_conn=ec2_conn,
                                          instance_profile=instance_profile,
                                          ipa_client=ipa_client,
                                          ec2_instances=ec2_instances,
                                          masters=masters))
        return

    return deploy_grp
