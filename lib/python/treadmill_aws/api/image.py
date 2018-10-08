"""Treadmill AWS image API.
"""

import logging

from treadmill import authz
from treadmill import exc

from treadmill_aws import ec2client
from treadmill_aws import awscontext
from treadmill_aws import userdata as ud
from treadmill_aws.cli import admin as aws_cli_admin


_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-statements
class API:
    """AWS Image REST api."""

    def __init__(self,
                 account=None,
                 instance_profile=None,
                 secgroup=None,
                 subnet=None):

        self._account = str(account)
        self._instance_profile = instance_profile
        self._secgroup = secgroup
        self._subnet = subnet

        def _list(account=None):
            """List configured monitors."""
            _LOGGER.info('list: account=%s', account)
            ec2_conn = awscontext.GLOBAL.ec2
            if not account:
                account = self._account

            image = {}
            return ec2client.list_images(ec2_conn, owners=[account], **image)

        def get(rsrc_id, account=None):
            """Get AWS image configuration."""
            _LOGGER.info('get: %s', rsrc_id)
            ec2_conn = awscontext.GLOBAL.ec2
            if not account:
                account = self._account

            image = {
                'name': rsrc_id
            }
            return ec2client.get_image(
                ec2_conn, owners=[account], **image
            )

        def create(rsrc_id, rsrc):
            """Create (configure) AWS image."""
            image = rsrc_id
            _LOGGER.info('Create image: %s', image)

            ec2_conn = awscontext.GLOBAL.ec2
            sts_conn = awscontext.GLOBAL.sts

            # Check if image exists. Create is async, so this is optimization
            # to return Found early.
            found = False
            try:
                get(image)
                found = True
            except Exception as _err:  # pylint: disable=broad-except
                # TODO: catch appropriate exception.
                pass

            if found:
                raise exc.FoundError('Image {} already exists.'.format(image))

            base_image_account = rsrc.get('base_image_account')
            _LOGGER.info('base account: %s', base_image_account)

            base_image = rsrc.get('base_image')
            base_image_id = aws_cli_admin.image_id(
                ec2_conn, sts_conn, base_image, account=base_image_account)
            _LOGGER.info('base image id: %s', base_image_id)

            secgroup = rsrc.get('secgroup')
            if secgroup:
                secgroup_id = aws_cli_admin.secgroup_id(ec2_conn, secgroup)
            else:
                secgroup_id = self._secgroup
            _LOGGER.info('secgroup id: %s', secgroup_id)

            subnet = rsrc.get('subnet')
            if subnet:
                subnet_id = aws_cli_admin.subnet_id(ec2_conn, subnet)
            else:
                subnet_id = self._subnet
            _LOGGER.info('subnet id: %s', secgroup_id)

            key = rsrc.get('key')

            cloud_init = ud.CloudInit()
            for content in rsrc.get('userdata', []):
                cloud_init.add(content)

            cloud_init.add_cloud_config({
                'image_description': '',
                'image_name': image,
            })

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

            _LOGGER.info(
                'Started instance: %s', instance['Instances'][0]['InstanceId']
            )

            return {
                'instance': instance['Instances'][0]['InstanceId']
            }

        def delete(rsrc_id):
            """Delete AWS image."""
            image = rsrc_id
            _LOGGER.info('Create image: %s', image)

            ec2_conn = awscontext.GLOBAL.ec2
            sts_conn = awscontext.GLOBAL.sts
            ec2client.delete_images(ec2_conn, name=image)

        self.list = _list
        self.get = get
        self.create = create
        self.delete = delete


def init(authorizer):
    """Returns module API wrapped with authorizer function."""
    api = API()
    return authz.wrap(api, authorizer)
