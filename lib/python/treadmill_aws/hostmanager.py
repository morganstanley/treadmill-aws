""" Module defining interface to create/delete/list IPA-joined hosts on AWS.
"""
import time

from treadmill_aws import ec2client


def _instance_tags(hostname, role):
    """Create list of AWS tags from manifest."""
    tags = [{'Key': 'Name', 'Value': hostname.lower()},
            {'Key': 'Role', 'Value': role.lower()}]
    return [{'ResourceType': 'instance', 'Tags': tags}]


def generate_hostname(domain, image):
    """Generates hostname from role, domain and timestamp."""
    timestamp = str(time.time()).replace('.', '')
    return '{}-{}.{}'.format(image.lower(), timestamp, domain)


def create_host(ec2_conn, ipa_client, image_id, count, domain,
                key, secgroup_ids, instance_type, subnet_id, disk,
                role=None,
                instance_profile=None):
    """Adds host defined in manifest to IPA, then adds the OTP from the
       IPA reply to the manifest and creates EC2 instance.
    """
    if role is None:
        role = 'generic'

    hosts = []

    for _ in range(count):
        hostname = generate_hostname(domain=domain, image=image_id)
        ipa_host = ipa_client.enroll_host(hostname=hostname)
        otp = ipa_host['result']['result']['randompassword']
        user_data = "#cloud-config\nhostname: %s\notp: %s" % (hostname, otp)

        ec2client.create_instance(
            ec2_conn,
            user_data=user_data,
            image_id=image_id,
            instance_type=instance_type,
            key=key,
            tags=_instance_tags(hostname, role),
            secgroup_ids=secgroup_ids,
            subnet_id=subnet_id,
            instance_profile=instance_profile,
            disk=disk
        )
        hosts.append(hostname)

    return hosts


def delete_hosts(ec2_conn, ipa_client, hostnames):
    """ Unenrolls hosts from IPA and AWS """
    for hostname in hostnames:
        ipa_client.unenroll_host(hostname=hostname)

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
