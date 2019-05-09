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


# pylint: disable=too-many-statements
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
    @click.option(
        '--match',
        type=aws_cli.IMAGE,
        required=False,
        help='image name, id, or tag (key=value)'
    )
    @click.argument(
        'image',
        required=False,
        type=aws_cli.IMAGE
    )
    @cli.admin.ON_EXCEPTIONS
    def _list(account, image, match):
        """List images"""
        ec2_conn = awscontext.GLOBAL.ec2
        if not account:
            account = 'self'

        if not image:
            image = {}

        if not match:
            match = {}

        images = ec2client.list_images(ec2_conn,
                                       owners=[account],
                                       **match)
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
            account = 'self'

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
        help='Instance profile with create image privs.'
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
        help='SSH key'
    )
    @click.argument('image', required=True, type=str)
    @cli.admin.ON_EXCEPTIONS
    def create(base_image, base_image_account, userdata, instance_profile,
               secgroup, subnet, image, key):
        """Create image"""
        ec2_conn = awscontext.GLOBAL.ec2

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
            ec2_conn, base_image, account=base_image_account)
        secgroup_id = aws_cli.admin.secgroup_id(ec2_conn, secgroup)
        subnet_id = aws_cli.admin.subnet_id(ec2_conn, subnet)
        tags = [{'ResourceType': 'instance',
                 'Tags': [{'Key': 'Name',
                           'Value': 'ImageBuild-{}'.format(image)}]}]

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
            disk=10
        )
        click.echo(instance['Instances'][0]['InstanceId'])

    @image.command(name='create-from-snapshot')
    @click.option('--snapshot',
                  type=aws_cli.SNAPSHOT,
                  required=True)
    @click.argument('image', required=True)
    def create_from_snapshot(snapshot, image):
        """Create image from snapshot."""

        ec2_conn = awscontext.GLOBAL.ec2

        snapshot = ec2client.get_snapshot(ec2_conn, **snapshot)

        snapshot_tag = {}
        for kv in snapshot['Tags']:
            key = kv['Key']
            value = kv['Value']
            if value == 'True':
                value = True
            if value == 'False':
                value = False
            snapshot_tag[key] = value

        kwargs = {}
        kwargs['Name'] = image
        kwargs['Architecture'] = snapshot_tag['Architecture']
        kwargs['EnaSupport'] = snapshot_tag['EnaSupport']
        kwargs['RootDeviceName'] = snapshot_tag['Device']
        kwargs['BlockDeviceMappings'] = [
            {
                'DeviceName': snapshot_tag['Device'],
                'Ebs': {
                    'SnapshotId': snapshot['SnapshotId'],
                }
            }
        ]
        kwargs['VirtualizationType'] = snapshot_tag['VirtualizationType']

        image = ec2_conn.register_image(**kwargs)
        print(image['ImageId'])

    @image.command(name='share')
    @click.option(
        '--account',
        required=True,
        help='Account ID.'
    )
    @click.argument('image', required=True, type=str)
    @cli.admin.ON_EXCEPTIONS
    def share(account, image):
        """Share Image"""
        ec2_conn = awscontext.GLOBAL.ec2
        ec2client.get_image(ec2_conn, ids=[image])

        share_image = ec2_conn.modify_image_attribute(
            ImageId=image,
            Attribute='launchPermission',
            OperationType='add',
            UserIds=[
                account
            ]
        )

        click.echo('%s has been shared with %s' % (image, account))

    @image.command(name='delete')
    @click.argument('image', required=True, type=aws_cli.IMAGE)
    @cli.admin.ON_EXCEPTIONS
    def delete(image):
        """Delete Image"""
        ec2_conn = awscontext.GLOBAL.ec2
        ec2client.delete_images(
            ec2_conn=ec2_conn,
            ids=image['ids']
        )

        click.echo(image)

    del _list
    del configure
    del create
    del delete

    return image
