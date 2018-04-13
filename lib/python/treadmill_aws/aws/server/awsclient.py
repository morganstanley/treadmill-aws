""" AWS client connectors and helper functions """
from treadmill_aws.infra import connection


def build_tags(hostname, role):
    """ Create list of AWS tags from manifest """
    tags = [{'Key': 'Name', 'Value': hostname.lower()},
            {'Key': 'Role', 'Value': role.upper()}]
    return [{'ResourceType': 'instance', 'Tags': tags}]


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


class AWSClient():
    """ Interfaces with AWS connection to create/delete/list EC2 instances
        Requires user has AWS credentials with EC2 permissions present in env
    """

    def __init__(self):
        self.ec2_conn = connection.Connection()

    def create_instance(self, domain, hostname, image_id, instance_type, key,
                        otp, proxy, role, secgroup_ids, subnet_id):
        """ Add new instance to AWS """
        tags = build_tags(hostname=hostname, role=role)
        user_data = render_manifest(domain=domain,
                                    hostname=hostname,
                                    otp=otp,
                                    proxy=proxy)

        self.ec2_conn.run_instances(
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

    def delete_instance(self, hostname):
        """ Delete instances matching hostname from AWS """
        instances = self.get_instances_by_hostname(hostname=hostname)

        for instance in instances:
            self.ec2_conn.terminate_instances(
                InstanceIds=[instance['InstanceId']],
                DryRun=False)

    def get_instances_by_hostname(self, hostname):
        """ Returns list of AWS instances that match hostname
            AWS returns instances in nested list- flatten to simple list
        """
        filters = [{'Name': 'tag:Name', 'Values': [hostname]},
                   {'Name': 'instance-state-name', 'Values': ['running']}]
        reservations = [
            x['Instances'] for x in
            self.ec2_conn.describe_instances(Filters=filters)['Reservations']]
        return [result
                for reservation in reservations
                for result in reservation]
