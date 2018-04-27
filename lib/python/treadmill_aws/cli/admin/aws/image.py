"""Implementation of treadmill admin EC2 image.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import gzip
import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import ec2client


def init():

    """EC2 image CLI group"""
    formatter = cli.make_formatter('aws_image')

    _account = awscontext.GLOBAL.sts.get_caller_identity().get('Account')

    @click.group()
    def image():
        """Manage image configuration"""
        pass

    @image.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List images"""
        ec2_conn = awscontext.GLOBAL.ec2
        images = ec2client.list_images(ec2_conn, owners=[_account])
        cli.out(formatter(images))

    @image.command(
        name='create'
    )
    @click.option(
        '--userdata', required=True,
        help='EC2 Userdata <path>'
    )
    @click.option(
        '--base-image-id', required=True,
        help='EC2 AMI ID'
    )
    @click.option(
        '--image-name', required=True,
        help='EC2 AMI Name Tag'
    )
    @click.option(
        '--image-version', required=True,
        help='EC2 AMI Version Tag'
    )
    @click.option(
        '--image-instance-type', required=True,
        help='EC2 Instance Type'
    )
    @click.option(
        '--image-instance-key', required=True,
        help='EC2 SSH Key'
    )
    @click.option(
        '--image-instance-role', required=True,
        help='EC2 Instance Role'
    )
    @click.option(
        '--image-instance-secgroup-ids', required=True,
        help='EC2 Instance SecurityGroups'
    )
    @click.option(
        '--image-subnet-id', required=True,
        help='EC2 Instance Subnet'
    )
    @cli.admin.ON_EXCEPTIONS
    def create(
            userdata, base_image_id, image_name, image_version,
            image_instance_type, image_instance_key, image_instance_role,
            image_instance_secgroup_ids, image_subnet_id
    ):
        """Create image"""
        ec2_conn = awscontext.GLOBAL.ec2

        with gzip.open(userdata, 'rb') as f:
            cloud_init = f.read()

        base_image = ec2client.get_image_by_id(ec2_conn, base_image_id)

        tags = {'Name': image_name, 'Version': image_version}

        images_by_tags = ec2client.list_images_by_tags(
            ec2_conn, tags, owners=[_account]
        )

        assert not images_by_tags, \
            "EC2 AMI with the Name: %s and Version: %s tags already exist" \
            % (image_name, image_version)

        instance_id = ec2client.create_image(
            ec2_conn, image_name, cloud_init, base_image_id,
            image_instance_type, image_instance_key, image_instance_role,
            image_instance_secgroup_ids, image_subnet_id, image_version
        )

        print("\nA new Treadmill image will be derived from %s" % instance_id)

    del _list
    del create

    return image
