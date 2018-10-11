""" Module defining interface to create/delete/list IPA-joined hosts on AWS.
"""
import logging
import time
import yaml

from treadmill_aws import aws
from treadmill_aws import ec2client
from treadmill_aws import ipaclient


_LOGGER = logging.getLogger(__name__)


def _instance_tags(hostname, role):
    """Create list of AWS tags from manifest."""
    tags = [{'Key': 'Name', 'Value': hostname.lower()},
            {'Key': 'Role', 'Value': role.lower()}]
    return [{'ResourceType': 'instance', 'Tags': tags}]


def render_manifest(key_value_pairs):
    """Returns formatted cloud-init from dictionary k:v pairs"""

    return "#cloud-config\n" + yaml.dump(
        key_value_pairs, default_flow_style=False, default_style='\'')


def generate_hostname(domain, hostname):
    """If hostname defined, returns FQDN.
       If not, returns FQDN with base32 timestamp.
    """

    # Take time.time() - float, then:
    # - remove period
    # - truncate to 17 digits
    # - if it happen that last digits are 0 (and will not be displayed, so
    #   string is shorter - pad it with 0.
    #
    # The result ensures that timestamp is 17 char length and is increasing.
    timestamp = str(time.time()).replace('.', '')[:17].ljust(17, '0')
    b32time = aws.int2str(number=int(timestamp), base=32)

    if hostname[-1] == '-':
        hostname = '{}{}'.format(hostname, '{time}')

    return '{}.{}'.format(hostname.format(time=b32time), domain)


def create_host(ec2_conn, ipa_client, image_id, count, domain,
                secgroup_ids, instance_type, subnet_id, disk,
                instance_vars, role=None, instance_profile=None,
                hostgroups=None, hostname=None, ip_address=None,
                eni=None, key=None):
    """Adds host defined in manifest to IPA, then adds the OTP from the
       IPA reply to the manifest and creates EC2 instance.
    """
    if hostgroups is None:
        hostgroups = []

    if role is None:
        role = 'generic'

    if instance_vars is None:
        instance_vars = {}

    if hostname is None:
        hostname = '{}-{}'.format(role.lower(), '{time}')

    hosts = []
    for _ in range(count):
        host_ctx = instance_vars.copy()

        host_ctx['hostname'] = generate_hostname(domain=domain,
                                                 hostname=hostname)
        if host_ctx['hostname'] in hosts:
            raise IndexError("Duplicate hostname")

        ipa_host = ipa_client.enroll_host(hostname=host_ctx['hostname'])
        host_ctx['otp'] = ipa_host['result']['result']['randompassword']
        user_data = render_manifest(host_ctx)

        for hostgroup in hostgroups:
            ipa_client.hostgroup_add_member(hostgroup, host_ctx['hostname'])

        tags = _instance_tags(host_ctx['hostname'], role)
        _LOGGER.debug(
            'Create EC2 instance: %s %s %s %s %r %r %s %s %s %s',
            host_ctx['hostname'],
            image_id,
            instance_type,
            key,
            secgroup_ids,
            subnet_id,
            instance_profile,
            disk,
            ip_address,
            eni
        )

        ec2client.create_instance(
            ec2_conn,
            user_data=user_data,
            image_id=image_id,
            instance_type=instance_type,
            key=key,
            tags=tags,
            secgroup_ids=secgroup_ids,
            subnet_id=subnet_id,
            instance_profile=instance_profile,
            disk=disk,
            ip_address=ip_address,
            eni=eni
        )
        hosts.append(host_ctx['hostname'])

    return hosts


def delete_hosts(ec2_conn, ipa_client, hostnames):
    """ Unenrolls hosts from IPA and AWS """
    for hostname in hostnames:
        _LOGGER.debug('Unenroll host from IPA: %s', hostname)
        try:
            ipa_client.unenroll_host(hostname=hostname)
        except (KeyError, ipaclient.NotFoundError):
            _LOGGER.debug('Host not found: %s', hostname)

    _LOGGER.debug('Delete instances: %r', hostnames)
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
