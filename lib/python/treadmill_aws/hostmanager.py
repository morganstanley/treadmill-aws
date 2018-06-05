""" Module defining interface to create/delete/list IPA-joined hosts on AWS.
"""
import time
import yaml

from treadmill_aws import ec2client
from treadmill_aws import ipaclient


def _instance_tags(hostname, role):
    """Create list of AWS tags from manifest."""
    tags = [{'Key': 'Name', 'Value': hostname.lower()},
            {'Key': 'Role', 'Value': role.lower()}]
    return [{'ResourceType': 'instance', 'Tags': tags}]


def render_manifest(key_value_pairs):
    """ Stub function to supply instance user_data during testing. """

    return "#cloud-config\n" + yaml.dump(
        key_value_pairs, default_flow_style=False)


def generate_hostname(domain, image):
    """Generates hostname from role, domain and timestamp."""
    timestamp = str(time.time()).replace('.', '')
    return '{}-{}.{}'.format(image.lower(), timestamp, domain)


def create_host(ec2_conn, ipa_client, image_id, count, domain,
                key, secgroup_ids, instance_type, subnet_id, disk,
                instance_vars, role=None, instance_profile=None):
    """Adds host defined in manifest to IPA, then adds the OTP from the
       IPA reply to the manifest and creates EC2 instance.
    """
    if role is None:
        role = 'generic'

    if instance_vars is None:
        instance_vars = {}

    hosts = []
    for _ in range(count):
        host_ctx = instance_vars.copy()
        host_ctx['hostname'] = generate_hostname(domain=domain, image=image_id)
        ipa_host = ipa_client.enroll_host(hostname=host_ctx['hostname'])
        host_ctx['otp'] = ipa_host['result']['result']['randompassword']
        user_data = render_manifest(host_ctx)

        ec2client.create_instance(
            ec2_conn,
            user_data=user_data,
            image_id=image_id,
            instance_type=instance_type,
            key=key,
            tags=_instance_tags(host_ctx['hostname'], role),
            secgroup_ids=secgroup_ids,
            subnet_id=subnet_id,
            instance_profile=instance_profile,
            disk=disk
        )
        hosts.append(host_ctx['hostname'])

    return hosts


def delete_hosts(ec2_conn, ipa_client, hostnames):
    """ Unenrolls hosts from IPA and AWS """
    for hostname in hostnames:
        try:
            ipa_client.unenroll_host(hostname=hostname)
        except (KeyError, ipaclient.NotFoundError):
            pass

    ec2client.delete_instances(ec2_conn, hostnames=hostnames)


def find_hosts(ipa_client, pattern=None):
    """ Returns list of matching hosts from IPA.
        If no pattern is provided, returns all hosts.
    """
    if pattern is None:
        pattern = ''

    return ipa_client.get_hosts(
        pattern=pattern
    )


def is_space_available(subnets):
    """ Returns total available IPs. """
    total_available_ips = sum(
        [subnet[0]['AvailableIpAddressCount'] for subnet in subnets]
    )

    return total_available_ips


def get_availability(subnet):
    """ Returns subnet`s total and available IPs. """
    subnet_available_ips = subnet[0]['AvailableIpAddressCount']
    subnet_cidr = subnet[0]['CidrBlock']
    subnet_total_ips = pow(
        2, (32 - int(subnet_cidr[subnet_cidr.find('/') + 1:]))
    )

    return subnet_available_ips, subnet_total_ips


def get_availability_rate(placements):
    """ Returns subnet`s availability rate. """
    availability_rate = {}

    for network, availability in placements.items():
        availability_rate[network] = (availability[0] * 100) / \
            availability[1]

    availability_rate = [(v, k) for k, v in availability_rate.items()]
    availability_rate.sort(reverse=True)
    availability_rate = [(k, v) for v, k in availability_rate]

    return availability_rate


def run_ec2(placements, best_placement, ipa_client, ec2_conn, image_id,
            count, disk, domain, key, secgroup_ids, instance_type, role,
            instance_vars):
    """ Run EC2 instance(s) in the best subnet. """
    hostnames = []

    for network in best_placement:
        subnet_available_ips = placements[network[0]][0]

        if subnet_available_ips < count:
            hostnames.append(
                create_host(
                    ipa_client=ipa_client,
                    ec2_conn=ec2_conn,
                    image_id=image_id,
                    count=subnet_available_ips,
                    disk=disk,
                    domain=domain,
                    key=key,
                    secgroup_ids=secgroup_ids,
                    instance_type=instance_type,
                    subnet_id=network[0],
                    role=role,
                    instance_vars=instance_vars,
                )
            )

            count -= subnet_available_ips

            continue

        elif subnet_available_ips >= count:
            hostnames.append(
                create_host(
                    ipa_client=ipa_client,
                    ec2_conn=ec2_conn,
                    image_id=image_id,
                    count=count,
                    disk=disk,
                    domain=domain,
                    key=key,
                    secgroup_ids=secgroup_ids,
                    instance_type=instance_type,
                    subnet_id=network[0],
                    role=role,
                    instance_vars=instance_vars,
                )
            )

            break

    return hostnames
