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

    del _list
    del configure

    return instance
