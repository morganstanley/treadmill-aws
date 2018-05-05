"""Implementation of treadmill admin EC2 image.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import gzip
import io

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import metadata
from treadmill_aws import cli as aws_cli
from treadmill_aws import userdata as ud


def init():

    """EC2 image CLI group"""
    formatter = cli.make_formatter('aws_image')

    @click.group()
    def image():
        """Manage image configuration"""
        pass

    @image.command(name='list')
    @click.option(
        '--account', required=False,
        help='Image account, defaults to current.'
    )
    @click.argument(
        'image',
        required=False,
        type=aws_cli.IMAGE
    )
    @cli.admin.ON_EXCEPTIONS
    def _list(account, image):
        """List images"""
        ec2_conn = awscontext.GLOBAL.ec2
        if not account:
            account = awscontext.GLOBAL.sts.get_caller_identity().get(
                'Account'
            )
        if not image:
            image = {}
        images = ec2client.list_images(ec2_conn, owners=[account], **image)
        cli.out(formatter(images))

    @image.command()
    @click.option(
        '--account', required=False,
        help='Image account, defaults to current.'
    )
    @click.argument(
        'image',
        required=False,
        type=aws_cli.IMAGE
    )
    def configure(account, image):
        """Configure AMI image."""
        if not image:
            image = {'ids': [metadata.image_id()]}

        ec2_conn = awscontext.GLOBAL.ec2

        owners = []
        if not account:
            account = awscontext.GLOBAL.sts.get_caller_identity().get(
                'Account'
            )

        image_obj = ec2client.get_image(ec2_conn, owners=[account], **image)
        cli.out(formatter(image_obj))

    @image.command(name='create')
    @click.option(
        '--base-image',
        required=True,
        type=aws_cli.IMAGE,
        help='Base image.'
    )
    @click.option(
        '--base-image-account',
        required=False,
        help='Base image account.'
    )
    @click.option(
        '--userdata',
        required=True,
        type=click.Path(exists=True),
        multiple=True,
        help='Cloud-init user data.'
    )
    @click.option(
        '--instance-profile',
        required=True,
        help='IAM profile with create image privs.'
    )
    @click.option(
        '--secgroup',
        required=True,
        type=aws_cli.SECGROUP,
        help='Security group'
    )
    @click.option(
        '--subnet',
        required=True,
        type=aws_cli.SUBNET,
        help='Subnet'
    )
    @click.option(
        '--key',
        required=True,
        help='SSH key'
    )
    @click.argument('image', required=True, type=str)
    @cli.admin.ON_EXCEPTIONS
    def create(base_image, base_image_account, userdata, instance_profile,
               secgroup, subnet, key, image):
        """Create image"""
        ec2_conn = awscontext.GLOBAL.ec2
        sts_conn = awscontext.GLOBAL.sts

        cloud_init = ud.CloudInit()
        for filename in userdata:
            with io.open(filename, 'rb') as f:
                content = f.read()
                if filename.endswith('.gz'):
                    content = gzip.decompress(content)

                cloud_init.add(content.decode())

        cloud_init.add_cloud_config({
            'image_description': '',
            'image_name': image,
        })

        base_image_id = aws_cli.admin.image_id(
            ec2_conn, sts_conn, base_image, account=base_image_account)
        secgroup_id = aws_cli.admin.secgroup_id(ec2_conn, secgroup)
        subnet_id = aws_cli.admin.subnet_id(ec2_conn, subnet)
        tags = []

        instance = ec2client.create_instance(
            ec2_conn,
            user_data=cloud_init.userdata(),
            image_id=base_image_id,
            instance_type='t2.small',
            key=key,
            tags=tags,
            secgroup_ids=secgroup_id,
            subnet_id=subnet_id,
            instance_profile=instance_profile,
        )
        print(instance)

    del _list
    del configure
    del create

    return image
