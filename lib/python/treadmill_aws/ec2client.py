""" AWS client connectors and helper functions """

from . import aws


def create_instance(ec2_conn, hostname, user_data, image_id, instance_type,
                    key, role, secgroup_ids, subnet_id, version=None):
    """Add new instance."""
    tags = aws.build_tags(hostname=hostname, role=role, version=version)
    return ec2_conn.run_instances(
        TagSpecifications=tags,
        ImageId=image_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName=key,
        UserData=user_data,
        NetworkInterfaces=[{
            'DeviceIndex': 0,
            'SubnetId': subnet_id,
            'Groups': [secgroup_ids]}]).get('Instances', [])


def delete_instance(ec2_conn, hostname):
    """Delete instances matching hostname."""
    instance = get_instance_by_hostname(ec2_conn, hostname)
    if instance:
        ec2_conn.terminate_instances(
            InstanceIds=[instance['InstanceId']],
            DryRun=False
        )


def get_instance_by_hostname(ec2_conn, hostname):
    """Returns list of AWS instances that match hostname.
    """
    # What is the point of filter by running state?
    filters = [
        {
            'Name': 'tag:Name',
            'Values': [hostname]
        },
        {
            'Name': 'instance-state-name',
            'Values': [
                'running',
                'pending',
                'shutting-down',
                'stopping',
                'stopped'
            ]
        }
    ]

    instances = list_instances(ec2_conn, filters=filters)
    if not instances:
        raise aws.NotFoundError()

    # TODO: need to check that hostname constraint returned one instance.
    assert len(instances) == 1
    return instances[0]


def get_instance_by_id(ec2_conn, instance_id):
    """Returns list of AWS instances that match instance id.
    """
    reservations = ec2_conn.describe_instances(
        InstanceIds=[instance_id]
    )['Reservations']
    instances = []
    for reservation in reservations:
        instances.extend(reservation['Instances'])

    if not instances:
        raise aws.NotFoundError()

    # TODO: need to check that only single instance is returned.
    assert len(instances) == 1
    return instances[0]


def list_instances(ec2_conn, match_hostname=None, filters=None):
    """Return list of instances matching filter.
    """
    instances = []
    if not filters:
        filters = []
    if match_hostname:
        filters.append({'Name': 'tag:Name', 'Values': [match_hostname]})

    reservations = ec2_conn.describe_instances(Filters=filters)['Reservations']
    for reservation in reservations:
        instances.extend(reservation['Instances'])
    return instances


def list_instances_by_tags(ec2_conn, tags):
    """Return list of instances matching all tags."""
    return list_instances(
        ec2_conn,
        match_hostname=None,
        filters=aws.build_tags_filter(tags)
    )


def get_instance_by_tags(ec2_conn, tags):
    """Return instance_id matching tags."""
    instances = list_instances_by_tags(ec2_conn, tags)
    if not instances:
        raise aws.NotFoundError('Instance with tags %r does not exist' % tags)

    instance = instances.pop(0)
    if instances:
        raise aws.NotUniqueError()

    return instance


def get_instance_id_by_tags(ec2_conn, tags):
    """Return instance_id matching tags."""
    return get_instance_by_tags(ec2_conn, tags)['InstanceId']


def get_subnet_by_id(ec2_conn, subnet_id):
    """Return subnet by id, None if not found."""
    subnets = ec2_conn.describe_subnets(
        SubnetIds=[subnet_id]
    )['Subnets']
    return subnets[0]


def list_subnets(ec2_conn, filters=None):
    """List subnets."""
    if not filters:
        filters = []
    return ec2_conn.describe_subnets(Filters=filters).get('Subnets', [])


def list_subnets_by_tags(ec2_conn, tags):
    """Return list of instances matching all tags."""
    return list_subnets(
        ec2_conn,
        filters=aws.build_tags_filter(tags)
    )


def get_subnet_by_tags(ec2_conn, tags):
    """Return instance_id matching tags."""
    subnets = list_subnets_by_tags(ec2_conn, tags)
    if not subnets:
        raise aws.NotFoundError('Subnet with tags %r does not exist' % tags)

    subnet = subnets.pop(0)
    if subnets:
        raise aws.NotUniqueError()

    return subnet


def get_subnet_id_by_tags(ec2_conn, tags):
    """Return instance_id matching tags."""
    return get_subnet_by_tags(ec2_conn, tags)['SubnetId']


def get_vpc_by_id(ec2_conn, vpc_id):
    """Return vpc by id, None if not found."""
    vpcs = ec2_conn.describe_vpcs(
        VpcIds=[vpc_id]
    )['Vpcs']
    return vpcs[0]


def list_vpcs(ec2_conn, filters=None):
    """List vpcs."""
    if not filters:
        filters = []
    return ec2_conn.describe_vpcs(Filters=filters).get('Vpcs', [])


def list_vpcs_by_tags(ec2_conn, tags):
    """Return list of instances matching all tags."""
    return list_vpcs(
        ec2_conn,
        filters=aws.build_tags_filter(tags)
    )


def get_vpc_by_tags(ec2_conn, tags):
    """Return instance_id matching tags."""
    vpcs = list_vpcs_by_tags(ec2_conn, tags)
    if not vpcs:
        raise aws.NotFoundError('vpc with tags %r does not exist' % tags)

    vpc = vpcs.pop(0)
    if vpcs:
        raise aws.NotUniqueError()

    return vpc


def get_vpc_id_by_tags(ec2_conn, tags):
    """Return instance_id matching tags."""
    return get_vpc_by_tags(ec2_conn, tags)['VpcId']


def create_image(
        ec2_conn, image_name, cloud_init, base_image_id,
        image_instance_type, image_instance_key, image_instance_role,
        image_instance_secgroup_ids, image_subnet_id, image_version
):
    """Creates AWS AMI."""

    instance = create_instance(
        ec2_conn, image_name, cloud_init, base_image_id,
        image_instance_type, image_instance_key, image_instance_role,
        image_instance_secgroup_ids, image_subnet_id, image_version
    )

    return instance[0]['InstanceId']


def list_images(ec2_conn, filters=None, owners=None):
    """List images."""
    if not owners:
        owners = []
    elif not filters:
        filters = []
    return ec2_conn.describe_images(
        Owners=owners, Filters=filters).get('Images', [])


def list_images_by_tags(ec2_conn, tags, owners=None):
    """Return list of images matching all tags."""
    return list_images(
        ec2_conn,
        filters=aws.build_tags_filter(tags),
        owners=owners
    )


def get_image_by_id(ec2_conn, image_id):
    """Returns list of AWS AMIs that match AMI id.
    """
    image = ec2_conn.describe_images(
        ImageIds=[image_id]
    )['Images']

    if not image:
        raise aws.NotFoundError()

    assert len(image) == 1, \
        "There are more AMIs with the same AMI id."
    return image[0]
