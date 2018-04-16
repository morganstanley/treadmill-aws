"""Implementation of treadmill admin EC2 vpc.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import hostmanager


def init():

    """EC2 instance CLI group"""
    formatter = cli.make_formatter('ec2_instance')

    @click.group()
    def instance():
        """Manage instance configuration"""
        pass

    @instance.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List instances"""
        ec2_conn = awscontext.GLOBAL.ec2
        instances = ec2client.list_instances(ec2_conn)
        cli.out(formatter(instances))

    @instance.command()
    @click.option('--instance-id', help='EC2 instancs id')
    @click.argument('hostname')
    @cli.admin.ON_EXCEPTIONS
    def configure(instance_id, hostname):
        """Configure instance"""
        ec2_conn = awscontext.GLOBAL.ec2
        if instance_id:
            instance = ec2client.get_instance_by_id(ec2_conn, instance_id)
        else:
            instance = ec2client.get_instance_by_hostname(ec2_conn, hostname)
        if instance:
            cli.out(formatter(instance))
        else:
            # TODO: need to raise not found exception and let it be handled.
            click.echo('Not found', err=True)

    @instance.command()
    @click.option('--ami', required=True, help='AMI image ID')
    @click.option('--count', required=True, default=1, type=int,
                  help='Number of instances')
    @click.option('--key', required=True, help='Instance SSH key name')
    @click.option('--role', required=True, help='Instance role')
    @click.option('--secgroup', required=True,
                  help='Instance security group ID')
    @click.option('--size', required=True, default='t2.small',
                  help='Instance EC2 size')
    @click.option('--subnet', required=True, help='AWS Subnet ID')
    @cli.ON_CLI_EXCEPTIONS
    def create(ami, count, key, role, secgroup, size, subnet):
        """Create instance(s)"""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2
        ipa_domain = awscontext.GLOBAL.ipa_domain

        hostnames = hostmanager.create_host(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            image_id=ami,
            count=count,
            domain=ipa_domain,
            key=key,
            role=role,
            secgroup_ids=secgroup,
            instance_type=size,
            subnet_id=subnet
        )
        for hostname in hostnames:
            click.echo(hostname)

    @instance.command(name='delete')
    @click.argument('hostname')
    @cli.ON_CLI_EXCEPTIONS
    def delete(hostname):
        """Delete instance."""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2

        hostmanager.delete_hosts(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            hostnames=[hostname]
        )

    del _list
    del configure
    del delete

    return instance
