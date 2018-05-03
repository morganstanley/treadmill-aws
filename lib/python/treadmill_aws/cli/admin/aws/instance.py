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
from treadmill_aws import metadata
from treadmill_aws import cli as aws_cli


# TODO: these seem like common functions that belong to ec2client or some
#       high level helper module.
def _image_id(ec2_conn, sts_conn, image, account):
    """Resolve CLI image arguments to image id."""
    if not image:
        image = {'ids': [metadata.image_id()]}
    if not account:
        account = sts_conn.get_caller_identity().get('Account')
    return ec2client.get_image(ec2_conn, owners=[account], **image)['ImageId']


def _subnet_id(ec2_conn, subnet):
    """Resolve subnet CLI arguments to subnet id."""
    if not subnet:
        subnet = {'ids': [metadata.subnet_id()]}
    return ec2client.get_subnet(ec2_conn, **subnet)['SubnetId']


def _secgroup_id(ec2_conn, secgroup):
    """Resolve secgroup id from secgroup CLI arguments."""
    if not secgroup:
        secgroup = {'ids': [metadata.secgroup_id()]}
    return ec2client.get_secgroup(ec2_conn, **secgroup)['GroupId']


def init():

    """EC2 instance CLI group"""
    formatter = cli.make_formatter('aws_instance')

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
    @click.argument('instance', required=False, type=aws_cli.INSTANCE)
    @cli.admin.ON_EXCEPTIONS
    def configure(instance):
        """Configure instance"""
        if not instance:
            instance = {'ids': [metadata.instance_id()]}

        ec2_conn = awscontext.GLOBAL.ec2
        instance_obj = ec2client.list_instances(ec2_conn, **instance)
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
    @cli.ON_CLI_EXCEPTIONS
    def create(image, image_account, count, key, role, secgroup, size, subnet):
        """Create instance(s)"""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2
        sts_conn = awscontext.GLOBAL.sts

        ipa_domain = awscontext.GLOBAL.ipa_domain

        image_id = _image_id(ec2_conn, sts_conn, image, image_account)
        secgroup_id = _secgroup_id(ec2_conn, secgroup)
        subnet_id = _subnet_id(ec2_conn, subnet)

        if not key:
            key = metadata.instance_keys()[0]

        hostnames = hostmanager.create_host(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            image_id=image_id,
            count=count,
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
