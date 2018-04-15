""" Module defining interface to create/delete/list IPA-joined hosts on AWS.
"""
import time

from treadmill_aws import ec2client


def render_manifest(domain, hostname, otp, proxy):
    """ Stub function to supply instance user_data during testing. """
    template = '''#!/bin/bash
    hostnamectl set-hostname {hostname}
    echo "export http_proxy={proxy}" \
        >> /etc/profile.d/http_proxy.sh
    echo "export NO_PROXY=localhost,169.254.169.254,*.{domain}" \
        >> /etc/profile.d/http_proxy.sh
    echo "proxy={proxy}" >> /etc/yum.conf
    yum install -y ipa-client
    ipa-client-install \
    --no-krb5-offline-password \
    --enable-dns-updates \
    --password='{otp}' \
    --mkhomedir \
    --no-ntp \
    --unattended'''.format(proxy=proxy,
                           domain=domain,
                           hostname=hostname,
                           otp=otp)
    return template


def generate_hostname(domain='domain', role='role'):
    """Generates hostname from role, domain and timestamp."""
    timestamp = str(time.time()).replace('.', '')
    return '{}-{}.{}'.format(role.lower(), timestamp, domain)


def create_host(ec2_conn, ipa_client, image_id, count, domain,
                key, proxy, role, secgroup_ids, instance_type, subnet_id):
    """Adds host defined in manifest to IPA, then adds the OTP from the
       IPA reply to the manifest and creates EC2 instance.
    """
    hosts = []

    for _ in range(count):
        hostname = generate_hostname(domain=domain, role=role)
        ipa_host = ipa_client.enroll_ipa_host(hostname=hostname)
        otp = ipa_host['result']['result']['randompassword']
        user_data = render_manifest(domain=domain,
                                    hostname=hostname,
                                    otp=otp,
                                    proxy=proxy)

        ec2client.create_instance(
            ec2_conn,
            hostname=hostname,
            user_data=user_data,
            image_id=image_id,
            instance_type=instance_type,
            key=key,
            role=role,
            secgroup_ids=secgroup_ids,
            subnet_id=subnet_id
        )
        hosts.append(hostname)

    return hosts


def delete_hosts(ec2_conn, ipa_client, hostnames):
    """ Unenrolls hosts from IPA and AWS """
    for hostname in hostnames:
        ipa_client.unenroll_ipa_host(hostname=hostname)
        ec2client.delete_instance(ec2_conn, hostname=hostname)


def find_hosts(ipa_client, pattern=None):
    """ Returns list of matching hosts from IPA.
        If no pattern is provided, returns all hosts.
    """
    if pattern is None:
        pattern = ''

    return ipa_client.get_ipa_hosts(
        pattern=pattern
    )
