"""AWS client connectors and helper functions.
"""

from . import aws


def create_instance(ec2_conn, user_data, image_id, instance_type,
                    key, tags, secgroup_ids, subnet_id, disk,
                    instance_profile=None):
    """Create new instance."""
    args = {
        'TagSpecifications': tags,
        'ImageId': image_id,
        'MinCount': 1,
        'MaxCount': 1,
        'InstanceType': instance_type,
        'KeyName': key,
        'UserData': user_data,
        'NetworkInterfaces': [{
            'DeviceIndex': 0,
            'SubnetId': subnet_id,
            'Groups': [secgroup_ids]
        }],
        'BlockDeviceMappings': [{
            'DeviceName': '/dev/xvda',
            'Ebs': {'VolumeSize': disk}}]
    }

    if instance_profile:
        if instance_profile.startswith('arn:aws:iam::'):
            args['IamInstanceProfile'] = {
                'Arn': instance_profile
            }
        else:
            args['IamInstanceProfile'] = {
                'Name': instance_profile
            }

    response = ec2_conn.run_instances(**args)
    return response


def list_instances(ec2_conn, ids=None, tags=None, hostnames=None, state=None):
    """List EC2 instances based on search criteria."""
    instances = []
    filters = []

    if not ids:
        ids = []

    if tags:
        filters.extend(aws.build_tags_filter(tags))

    if hostnames:
        filters.append({'Name': 'tag:Name', 'Values': hostnames})

    if not state:
        filters.append({'Name': 'instance-state-name', 'Values': ['running']})
    else:
        filters.append({'Name': 'instance-state-name', 'Values': state})

    reservations = ec2_conn.describe_instances(
        InstanceIds=ids,
        Filters=filters
    )['Reservations']

    for reservation in reservations:
        instances.extend(reservation['Instances'])
    return instances


def get_instance(ec2_conn, ids=None, tags=None, hostnames=None, state=None):
    """Get single instance matching criteria.

    If more than one image match, raise exception NonUniqueError.
    """
    instances = list_instances(
        ec2_conn, ids=ids, tags=tags, hostnames=hostnames, state=state
    )
    instance = instances.pop(0)
    if instances:
        raise aws.NotUniqueError()

    return instance


def delete_instances(ec2_conn, ids=None, tags=None, hostnames=None,
                     state=None):
    """Delete instances matching criteria."""
    instances = list_instances(
        ec2_conn, ids=ids, tags=tags, hostnames=hostnames, state=state
    )

    instance_ids = [i['InstanceId'] for i in instances]
    if instance_ids:
        ec2_conn.terminate_instances(
            InstanceIds=instance_ids,
            DryRun=False
        )


def list_images(ec2_conn, ids=None, tags=None, owners=None, name=None):
    """List images."""
    if not owners:
        owners = []

    filters = []
    if tags:
        filters.extend(aws.build_tags_filter(tags))

    if name:
        filters.append({'Name': 'name', 'Values': [name]})

    if not ids:
        ids = []

    return ec2_conn.describe_images(
        ImageIds=ids,
        Filters=filters,
        Owners=owners
    ).get('Images', [])


def get_image(ec2_conn, ids=None, tags=None, owners=None, name=None):
    """Get single image matching criteria.

    If more than one image match, raise exception NonUniqueError.
    """
    images = list_images(
        ec2_conn, ids=ids, tags=tags, owners=owners, name=name
    )
    image = images.pop(0)
    if images:
        raise aws.NotUniqueError()

    return image


def list_secgroups(ec2_conn, ids=None, tags=None, names=None):
    """List security groups."""
    filters = []
    if tags:
        filters.extend(aws.build_tags_filter(tags))

    if not ids:
        ids = []

    if not names:
        names = []

    return ec2_conn.describe_security_groups(
        GroupIds=ids,
        Filters=filters,
        GroupNames=names,
    ).get('SecurityGroups', [])


def get_secgroup(ec2_conn, ids=None, tags=None, names=None):
    """Get single security group matching criteria.

    If more than one image match, raise exception NonUniqueError.
    """
    groups = list_secgroups(
        ec2_conn, ids=ids, tags=tags, names=names
    )
    group = groups.pop(0)
    if groups:
        raise aws.NotUniqueError()

    return group


def list_subnets(ec2_conn, ids=None, tags=None):
    """List subnets."""
    filters = []
    if tags:
        filters.extend(aws.build_tags_filter(tags))

    if not ids:
        ids = []

    return ec2_conn.describe_subnets(
        SubnetIds=ids,
        Filters=filters,
    ).get('Subnets', [])


def get_subnet(ec2_conn, ids=None, tags=None):
    """Get single subnet matching criteria.

    If more than one image match, raise exception NonUniqueError.
    """
    subnets = list_subnets(
        ec2_conn, ids=ids, tags=tags
    )
    subnet = subnets.pop(0)
    if subnets:
        raise aws.NotUniqueError()

    return subnet


def list_vpcs(ec2_conn, ids=None, tags=None):
    """List VPCs."""
    filters = []
    if tags:
        filters.extend(aws.build_tags_filter(tags))

    if not ids:
        ids = []

    return ec2_conn.describe_vpcs(
        VpcIds=ids,
        Filters=filters,
    ).get('Vpcs', [])


def get_vpc(ec2_conn, ids=None, tags=None):
    """Get single VPC matching criteria.

    If more than one image match, raise exception NonUniqueError.
    """
    vpcs = list_vpcs(
        ec2_conn, ids=ids, tags=tags
    )
    vpc = vpcs.pop(0)
    if vpcs:
        raise aws.NotUniqueError()

    return vpc
