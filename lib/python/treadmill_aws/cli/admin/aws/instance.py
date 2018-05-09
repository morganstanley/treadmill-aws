"""Implementation of treadmill admin EC2 vpc.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import hostmanager
from treadmill_aws import metadata
from treadmill_aws import cli as aws_cli


def init():

    """EC2 instance CLI group"""
    formatter = cli.make_formatter('aws_instance')

    @click.group()
    def instance():
        """Manage instance configuration"""
        pass

    @instance.command(name='list')
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def _list():
        """List instances"""
        ec2_conn = awscontext.GLOBAL.ec2
        instances = ec2client.list_instances(ec2_conn)
        cli.out(formatter(instances))

    @instance.command()
    @click.argument('instance', required=False, type=aws_cli.INSTANCE)
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def configure(instance):
        """Configure instance"""
        if not instance:
            instance = {'ids': [metadata.instance_id()]}

        ec2_conn = awscontext.GLOBAL.ec2
        instance_obj = ec2client.get_instance(ec2_conn, **instance)
        cli.out(formatter(instance_obj))

    @instance.command()
    @click.option(
        '--image',
        required=False,
        help='Image',
        type=aws_cli.IMAGE
    )
    @click.option(
        '--image-account',
        required=False,
        help='AWS image account.',
    )
    @click.option(
        '--secgroup',
        required=False,
        type=aws_cli.SECGROUP,
        help='Security group'
    )
    @click.option(
        '--subnet',
        required=False,
        type=aws_cli.SUBNET,
        help='Subnet'
    )
    @click.option(
        '--role',
        required=False,
        help='Instance role',
        default='generic'
    )
    @click.option(
        '--key',
        required=False,
        help='Instance SSH key name'
    )
    @click.option(
        '--size',
        required=True,
        default='t2.small',
        help='Instance EC2 size'
    )
    @click.option(
        '--count',
        required=True,
        default=1,
        type=int,
        help='Number of instances'
    )
    @click.option(
        '--disk-size',
        required=True,
        default=10,
        help='Root parition size',
        callback=aws_cli.convert_disk_size_to_int
    )
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def create(
            image, image_account, count, disk,
            key, role, secgroup, size, subnet):
        """Create instance(s)"""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2
        sts_conn = awscontext.GLOBAL.sts

        ipa_domain = awscontext.GLOBAL.ipa_domain

        image_id = aws_cli.admin.image_id(
            ec2_conn, sts_conn, image, image_account)
        secgroup_id = aws_cli.admin.secgroup_id(ec2_conn, secgroup)
        subnet_id = aws_cli.admin.subnet_id(ec2_conn, subnet)

        if not key:
            key = metadata.instance_keys()[0]

        hostnames = hostmanager.create_host(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            image_id=image_id,
            count=count,
            disk=disk,
            domain=ipa_domain,
            key=key,
            secgroup_ids=secgroup_id,
            instance_type=size,
            subnet_id=subnet_id,
            role=role,
        )
        for hostname in hostnames:
            click.echo(hostname)

    @instance.command(name='delete')
    @click.argument('hostname')
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
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
