""" Module defining interface to create/delete/list IPA-joined hosts on AWS.
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time
import yaml

from treadmill_aws import ec2client


def render_manifest(key_value_pairs, url_list=None):
    """ Stub function to supply instance user_data during testing. """
    combined_userdata = MIMEMultipart()

    # Format K:V pairs and attach to MIME message body
    combined_userdata.attach(MIMEText(yaml.dump(key_value_pairs),
                                      'cloud-config'))

    # Generate MIME from cloud-init template and attach to MIME message body
    domain_join_template = '''# install ipa-client
packages:
 - ipa-client
#
# Join domain
runcmd:
  - ipa-client-install \
  --no-krb5-offline-password \
  --enable-dns-updates \
  --password=`grep -E '^otp:[[:space:]]' \
             /var/lib/cloud/instance/cloud-config.txt \
             | tail -1 | awk '{print $2}'` \
  --mkhomedir \
  --no-ntp \
  --unattended'''
    combined_userdata.attach(MIMEText(domain_join_template, 'cloud-config'))

    # Format and attach any URL includes
    if url_list:
        combined_userdata.attach(
            MIMEText('\n'.join(url_list), 'x-include-once-url'))

    # Cast the MIME message to ascii so boto3 can base64 it without errors
    return combined_userdata.as_string().encode('ascii')


def generate_hostname(domain, role):
    """Generates hostname from role, domain and timestamp."""
    timestamp = str(time.time()).replace('.', '')
    return '{}-{}.{}'.format(role.lower(), timestamp, domain)


def create_host(ec2_conn, ipa_client, image_id, count, domain,
                key, role, secgroup_ids, instance_type, subnet_id):
    """Adds host defined in manifest to IPA, then adds the OTP from the
       IPA reply to the manifest and creates EC2 instance.
    """
    hosts = []

    for _ in range(count):
        hostname = generate_hostname(domain=domain, role=role)
        ipa_host = ipa_client.enroll_host(hostname=hostname)
        otp = ipa_host['result']['result']['randompassword']
        user_data = render_manifest(key_value_pairs={'hostname': hostname,
                                                     'otp': otp})

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
        ipa_client.unenroll_host(hostname=hostname)
        ec2client.delete_instance(ec2_conn, hostname=hostname)


def find_hosts(ipa_client, pattern=None):
    """ Returns list of matching hosts from IPA.
        If no pattern is provided, returns all hosts.
    """
    if pattern is None:
        pattern = ''

    return ipa_client.get_hosts(
        pattern=pattern
    )
