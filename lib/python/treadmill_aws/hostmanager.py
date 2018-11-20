""" Module defining interface to create/delete/list IPA-joined hosts on AWS.
"""
import logging
import random
import time
import yaml

from botocore import exceptions as botoexc

from treadmill import admin
from treadmill import context
from treadmill import sysinfo
from treadmill.syscall import krb5

from treadmill_aws import aws
from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import ipaclient


_LOGGER = logging.getLogger(__name__)
_EC2_DELETE_BATCH = 50


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
                secgroup_ids, instance_type, subnets, disk,
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

    account_aliases = awscontext.GLOBAL.iam.list_account_aliases()
    location = account_aliases['AccountAliases'].pop()
    hosts = []
    for _ in range(count):
        host_ctx = instance_vars.copy()

        host_ctx['hostname'] = generate_hostname(domain=domain,
                                                 hostname=hostname)
        if host_ctx['hostname'] in hosts:
            raise IndexError("Duplicate hostname")

        ipa_host = ipa_client.enroll_host(host_ctx['hostname'],
                                          location=location)
        host_ctx['otp'] = ipa_host['result']['result']['randompassword']
        user_data = render_manifest(host_ctx)

        for hostgroup in hostgroups:
            ipa_client.hostgroup_add_member(hostgroup, host_ctx['hostname'])

        tags = _instance_tags(host_ctx['hostname'], role)

        random.shuffle(subnets)

        for subnet in subnets:
            _LOGGER.debug(
                'Create EC2 instance: %s %s %s %s %r %r %s %s %s %s',
                host_ctx['hostname'],
                image_id,
                instance_type,
                key,
                secgroup_ids,
                subnet,
                instance_profile,
                disk,
                ip_address,
                eni
            )
            try:
                ec2client.create_instance(
                    ec2_conn,
                    user_data=user_data,
                    image_id=image_id,
                    instance_type=instance_type,
                    key=key,
                    tags=tags,
                    secgroup_ids=secgroup_ids,
                    subnet_id=subnet,
                    instance_profile=instance_profile,
                    disk=disk,
                    ip_address=ip_address,
                    eni=eni
                )
                hosts.append(host_ctx['hostname'])
                break
            except botoexc.ClientError as error:
                if error.response['Error']['Code'] == (
                        'InsufficientFreeAddressesInSubnet'):
                    _LOGGER.debug('Subnet full, trying next')
                    continue
                elif error.response['Error']['Code'] == (
                        'InsufficientInstanceCapacity'):
                    _LOGGER.debug('Instance not available in AZ, trying next')
                    continue
    return hosts


def delete_hosts(ec2_conn, ipa_client, hostnames):
    """ Unenrolls hosts from IPA and AWS
        EC2 imposes a maximum limit on the number of instances that can be
        selected using filters (200); delete instances in batches of
        _EC2_DELETE_BATCH
    """
    for hostname in hostnames:
        _LOGGER.debug('Unenroll host from IPA: %s', hostname)
        try:
            ipa_client.unenroll_host(hostname=hostname)
        except (KeyError, ipaclient.NotFoundError):
            _LOGGER.debug('Host not found: %s', hostname)

    _LOGGER.debug('Delete instances: %r', hostnames)
    while hostnames:
        batch = hostnames[:_EC2_DELETE_BATCH]
        hostnames = hostnames[_EC2_DELETE_BATCH:]
        ec2client.delete_instances(ec2_conn=ec2_conn, hostnames=batch)


def find_hosts(ipa_client, pattern=None):
    """ Returns list of matching hosts from IPA.
        If no pattern is provided, returns all hosts.
    """
    if pattern is None:
        pattern = ''

    return ipa_client.get_hosts(
        pattern=pattern
    )


def create_zk(
        ec2_conn,
        ipa_client,
        master,
        subnet_id=None,
        ip_address=None,
        instance_type=None):
    """ Create new Zookeeper """
    sts_conn = awscontext.GLOBAL.sts
    ipa_domain = awscontext.GLOBAL.ipa_domain

    admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
    cell = admin_cell.get(context.GLOBAL.cell)
    data = cell['data']

    image_id = data['image']
    if not image_id.startswith('ami-'):
        account = sts_conn.get_caller_identity().get('Account')
        image_id = ec2client.get_image(
            ec2_conn, owners=[account], name=image_id
        )['ImageId']

    # FIXME; subnet not unique among ZK, not AZ aware
    if not subnet_id:
        subnet_id = random.choice(data['subnets'])

    shortname = master['hostname'].replace('.' + context.GLOBAL.dns_domain, '')

    if not instance_type:
        instance_type = 'm5.large'

    # Instance vars
    instance_vars = {
        'treadmill_cell': context.GLOBAL.cell,
        'treadmill_ldap': ','.join(context.GLOBAL.ldap.url),
        'treadmill_ldap_suffix': context.GLOBAL.ldap_suffix,
        'treadmill_dns_domain': context.GLOBAL.dns_domain,
        'treadmill_isa': 'zookeeper',
        'treadmill_profile': 'aws',
        'treadmill_krb_realm': krb5.get_host_realm(sysinfo.hostname())[0],
        'treadmill_zookeeper_myid': str(master['idx']),
    }

    # Build user-data and start new instance
    create_host(ec2_conn=ec2_conn,
                ipa_client=ipa_client,
                image_id=image_id,
                count=1,
                domain=ipa_domain,
                secgroup_ids=data['secgroup'],
                instance_type=instance_type,
                subnets=[subnet_id],
                disk=30,
                instance_vars=instance_vars,
                role='zookeeper',
                hostgroups=['zookeepers'],
                hostname=shortname,
                ip_address=ip_address)

    return master['hostname']


def rotate_zk(ec2_conn, ipa_client, masters, ec2_instances):
    """ Determine which Zookeeper instance to rotate"""

    # Get oldest EC2 instance by LaunchTime
    old_master = min(ec2_instances, key=lambda x: x.get('LaunchTime'))

    # Parse instance data and extract hostname from tags:
    old_master_hostname = next(
        x.get('Value') for x in old_master.get('Tags')
        if x.get('Key') == "Name")

    # Retrieve cell Master record that matches hostname
    master = next(x for x in masters
                  if x.get('hostname') == old_master_hostname)

    return replace_zk(ec2_conn=ec2_conn,
                      ipa_client=ipa_client,
                      master=master,
                      old_master=old_master)


def replace_zk(ec2_conn, ipa_client, master, old_master):
    """ Delete and recreate oldest Zookeeper in quorum """
    # Remove server
    delete_hosts(ec2_conn, ipa_client, [master['hostname']])

    # Create server
    return create_zk(ec2_conn=ec2_conn,
                     ipa_client=ipa_client,
                     master=master,
                     instance_type=old_master.get('InstanceType', None),
                     subnet_id=old_master.get('SubnetId', None))
