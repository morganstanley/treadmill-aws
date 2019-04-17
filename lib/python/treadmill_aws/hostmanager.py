""" Module defining interface to create/delete/list IPA-joined hosts on AWS.
"""
import logging
import random
import time
import yaml

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


def _instance_tags(hostname, role, tags=None):
    """Return instance tags (common tags + instance name and role).
    """
    if tags is None:
        tags = []

    return [{
        'ResourceType': 'instance',
        'Tags': tags + [
            {'Key': 'Name', 'Value': hostname.lower()},
            {'Key': 'Role', 'Value': role.lower()},
        ],
    }]


def _instance_user_data(hostname, otp, instance_vars):
    """Return instance user data (common instance vars + hostname and otp)."""

    key_value_pairs = instance_vars.copy()
    key_value_pairs['hostname'] = hostname
    key_value_pairs['otp'] = otp

    return "#cloud-config\n" + yaml.dump(
        key_value_pairs, default_flow_style=False, default_style='\''
    )


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

    hostname = hostname.format(time=b32time)

    if not hostname.endswith(domain):
        hostname = '{}.{}'.format(hostname, domain)

    return hostname


@aws.profile
def create_otp(ipa_client, hostname, hostgroups, nshostlocation=None):
    """Create OTP."""
    _LOGGER.info('Creating OTP for %s', hostname)

    hostgroups = hostgroups or []

    if not nshostlocation:
        # FIXME: Make sure nshostlocation is always passed and remove that.
        account_aliases = awscontext.GLOBAL.iam.list_account_aliases()
        nshostlocation = account_aliases['AccountAliases'].pop()

    ipa_host = ipa_client.enroll_host(hostname, nshostlocation=nshostlocation)
    otp = ipa_host['result']['result']['randompassword']

    for hostgroup in hostgroups:
        ipa_client.hostgroup_add_member(hostgroup, hostname)

    return otp


@aws.profile
def create_host(ec2_conn, ipa_client, image_id, count, domain,
                secgroup_ids, instance_type, subnet, disk,
                instance_vars, role=None, instance_profile=None,
                hostgroups=None, hostname=None, ip_address=None,
                eni=None, key=None, tags=None, spot=False,
                nshostlocation=None, otp=None):
    """Adds host defined in manifest to IPA, then adds the OTP from the
       IPA reply to the manifest and creates EC2 instance.
    """
    instance_vars = instance_vars or {}

    if role is None:
        role = 'generic'

    if hostname is None:
        hostname = '{}-{}'.format(role.lower(), '{time}')

    instance_params = dict(
        image_id=image_id,
        instance_type=instance_type,
        key=key,
        secgroup_ids=secgroup_ids,
        instance_profile=instance_profile,
        disk=disk,
        ip_address=ip_address,
        eni=eni,
        spot=spot
    )

    hosts_created = []
    for _ in range(count):
        host = generate_hostname(domain=domain, hostname=hostname)
        if host in hosts_created:
            raise IndexError('Duplicate hostname')

        if not otp:
            otp = create_otp(
                ipa_client, host, hostgroups,
                nshostlocation=nshostlocation
            )

        instance_user_data = _instance_user_data(host, otp, instance_vars)
        instance_tags = _instance_tags(host, role, tags)

        _LOGGER.info(
            'Creating EC2 instance %s in subnet %s: %r %r %r',
            host, subnet, instance_vars, instance_tags, instance_params
        )
        ec2client.create_instance(
            ec2_conn,
            subnet_id=subnet,
            user_data=instance_user_data,
            tags=instance_tags,
            **instance_params
        )
        hosts_created.append(host)
    return hosts_created


def delete_hosts(ec2_conn, ipa_client, hostnames):
    """ Unenrolls hosts from IPA and AWS
        EC2 imposes a maximum limit on the number of instances that can be
        selected using filters (200); delete instances in batches of
        _EC2_DELETE_BATCH
    """
    _LOGGER.debug('Delete instances: %r', hostnames)
    hostnames_left = hostnames[:]
    while hostnames_left:
        batch = hostnames_left[:_EC2_DELETE_BATCH]
        hostnames_left = hostnames_left[_EC2_DELETE_BATCH:]
        ec2client.delete_instances(ec2_conn=ec2_conn, hostnames=batch)

    for hostname in hostnames:
        _LOGGER.debug('Unenroll host from IPA: %s', hostname)
        try:
            ipa_client.unenroll_host(hostname=hostname)
        except (KeyError, ipaclient.NotFoundError):
            _LOGGER.debug('Host not found: %s', hostname)


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
        instance_type=None,
        instance_profile=None):
    """ Create new Zookeeper """
    ipa_domain = awscontext.GLOBAL.ipa_domain

    admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
    cell = admin_cell.get(context.GLOBAL.cell)
    data = cell['data']

    image_id = data['image']
    if not image_id.startswith('ami-'):
        image_id = ec2client.get_image(
            ec2_conn, owners=['self'], name=image_id
        )['ImageId']

    # FIXME; subnet not unique among ZK, not AZ aware
    if not subnet_id:
        subnet_id = random.choice(data['subnets'])

    shortname = master['hostname'].replace('.' + context.GLOBAL.dns_domain, '')

    if not instance_type:
        instance_type = 'm5.large'

    if not instance_profile:
        instance_profile = 'zk-server'

    # Instance vars
    instance_vars = {
        'instance_profile': instance_profile,
        'treadmill_cell': context.GLOBAL.cell,
        'treadmill_ldap': ','.join(context.GLOBAL.ldap.url),
        'treadmill_ldap_suffix': context.GLOBAL.ldap_suffix,
        'treadmill_dns_domain': context.GLOBAL.dns_domain,
        'treadmill_isa': 'zookeeper',
        'treadmill_profile': 'aws',
        'treadmill_krb_realm': krb5.get_host_realm(sysinfo.hostname())[0],
        'treadmill_zookeeper_myid': str(master['idx']),
        'treadmill_zookeeper_admins': ','.join(set([cell['username'],
                                                    data['aws_admin']]))
    }

    # Build user-data and start new instance
    create_host(ec2_conn=ec2_conn,
                ipa_client=ipa_client,
                image_id=image_id,
                count=1,
                domain=ipa_domain,
                secgroup_ids=data['secgroup'],
                instance_type=instance_type,
                subnet=subnet_id,
                disk=30,
                instance_vars=instance_vars,
                role='zookeeper',
                hostgroups=['zookeepers'],
                hostname=shortname,
                ip_address=ip_address)

    return master['hostname']


def rotate_zk(ec2_conn, ec2_instances, instance_profile, ipa_client, masters):
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
                      instance_profile=instance_profile,
                      ipa_client=ipa_client,
                      master=master,
                      old_master=old_master)


def replace_zk(ec2_conn, instance_profile, ipa_client, master, old_master):
    """ Delete and recreate oldest Zookeeper in quorum """
    # Remove server
    delete_hosts(ec2_conn, ipa_client, [master['hostname']])

    # Create server
    return create_zk(ec2_conn=ec2_conn,
                     instance_profile=instance_profile,
                     ipa_client=ipa_client,
                     master=master,
                     instance_type=old_master.get('InstanceType', None),
                     subnet_id=old_master.get('SubnetId', None))
