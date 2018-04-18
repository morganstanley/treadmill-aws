""" AWS client connectors and helper functions """


def build_tags(hostname, role):
    """Create list of AWS tags from manifest."""
    tags = [{'Key': 'Name', 'Value': hostname.lower()},
            {'Key': 'Role', 'Value': role.lower()}]
    return [{'ResourceType': 'instance', 'Tags': tags}]


def create_instance(ec2_conn, hostname, user_data, image_id, instance_type,
                    key, role, secgroup_ids, subnet_id):
    """Add new instance."""
    tags = build_tags(hostname=hostname, role=role)
    ec2_conn.run_instances(
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
            'Groups': [secgroup_ids]}])


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
    filters = [{'Name': 'tag:Name', 'Values': [hostname]},
               {'Name': 'instance-state-name', 'Values': ['running']}]

    instances = list_instances(ec2_conn, filters=filters)
    if not instances:
        return None

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
        return None

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
