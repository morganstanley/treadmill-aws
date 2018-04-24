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


def init():

    """EC2 image CLI group"""
    formatter = cli.make_formatter('aws_image')

    @click.group()
    def image():
        """Manage image configuration"""
        pass

    @image.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    def _list():
        """List images"""
        ec2_conn = awscontext.GLOBAL.ec2
        _account = awscontext.GLOBAL.sts.get_caller_identity().get('Account')
        images = ec2client.list_images(ec2_conn, owners=[_account])
        cli.out(formatter(images))

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
