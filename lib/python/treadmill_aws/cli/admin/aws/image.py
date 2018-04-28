"""Implementation of treadmill admin EC2 image.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import metadata
from treadmill_aws.cli import options


def init():

    """EC2 image CLI group"""
    formatter = cli.make_formatter('aws_image')
    image_args = {}

    @click.group()
    def image():
        """Manage image configuration"""
        pass

    @image.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List images"""
        ec2_conn = awscontext.GLOBAL.ec2
        account = awscontext.GLOBAL.sts.get_caller_identity().get('Account')
        images = ec2client.list_images(ec2_conn, owners=[account])
        cli.out(formatter(images))

    @image.command()
    @options.make_image_opts(image_args)
    def configure():
        """Configure AMI image."""
        ec2_conn = awscontext.GLOBAL.ec2

        # TODO: may need better switch for public/private images.
        owners = []
        if 'owner' not in image_args:
            account = awscontext.GLOBAL.sts.get_caller_identity().get(
                'Account'
            )
            owners.append(account)
        else:
            owners.append(image_args['owner'])

        if image_args.get('tags', []):
            image = ec2client.get_image_by_tags(
                ec2_conn,
                image_args['tags'],
                owners=owners
            )
        elif image_args.get('name'):
            image_name = image_args['name']
            image = ec2client.get_image_by_name(
                ec2_conn,
                image_name,
                owners=owners
            )
        else:
            image_id = image_args.get('id', metadata.image_id())
            image = ec2client.get_image_by_id(
                ec2_conn,
                image_id
            )

        cli.out(formatter(image))

#   This is a create API dummy skelleton
    @image.command(name='create')
    @click.argument('image_id')
    @cli.admin.ON_EXCEPTIONS
    def create(image_id):
        """Create image"""
        ec2_conn = awscontext.GLOBAL.ec2
        image = ec2client.get_image_by_id(ec2_conn, image_id)
        cli.out(formatter(image))

    del _list
    del create

    return image
