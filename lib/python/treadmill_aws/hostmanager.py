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
        key_value_pairs, default_flow_style=False, default_style='\'')


def generate_hostname(domain, image):
    """Generates hostname from role, domain and timestamp."""
    timestamp = str(time.time()).replace('.', '')
    return '{}-{}.{}'.format(image.lower(), timestamp, domain)


def create_host(ec2_conn, ipa_client, image_id, count, domain,
                key, secgroup_ids, instance_type, subnet_id, disk,
                instance_vars, hostgroups=None, role=None,
                instance_profile=None):
    """Adds host defined in manifest to IPA, then adds the OTP from the
       IPA reply to the manifest and creates EC2 instance.
    """
    if hostgroups is None:
        hostgroups = []

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

        for hostgroup in hostgroups:
            ipa_client.hostgroup_add_member(hostgroup, host_ctx['hostname'])

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
