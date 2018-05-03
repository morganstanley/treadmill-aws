"""Helper functions."""

from treadmill_aws import ec2client
from treadmill_aws import metadata


def image_id(ec2_conn, sts_conn, image, account):
    """Resolve CLI image arguments to image id."""
    if not image:
        image = {'ids': [metadata.image_id()]}
    if not account:
        account = sts_conn.get_caller_identity().get('Account')
    return ec2client.get_image(ec2_conn, owners=[account], **image)['ImageId']


def subnet_id(ec2_conn, subnet):
    """Resolve subnet CLI arguments to subnet id."""
    if not subnet:
        subnet = {'ids': [metadata.subnet_id()]}
    return ec2client.get_subnet(ec2_conn, **subnet)['SubnetId']


def secgroup_id(ec2_conn, secgroup):
    """Resolve secgroup id from secgroup CLI arguments."""
    if not secgroup:
        secgroup = {'ids': [metadata.secgroup_id()]}
    return ec2client.get_secgroup(ec2_conn, **secgroup)['GroupId']
