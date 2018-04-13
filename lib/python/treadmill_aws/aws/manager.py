""" Module defining interface to create/delete/list IPA-joined hosts on AWS.
"""
import time

from treadmill_aws.aws.server.awsclient import AWSClient
from treadmill_aws.aws.server.ipaclient import IPAClient


def generate_hostname(domain='domain', role='role'):
    """ Generates hostname from role, domain and timestamp."""
    timestamp = str(time.time()).replace('.', '')
    return 'tm{}-{}.{}'.format(role.lower(),
                               timestamp,
                               domain)


class HostManager():
    """ Class to allow management of IPA-joined hosts in AWS. """
    def __init__(self):
        self.awsclient = AWSClient()
        self.ipaclient = IPAClient()

    def create_host(self, image_id, cert, count, domain, key, proxy, role,
                    secgroup_ids, instance_type, subnet_id):
        """ Adds host defined in manifest to IPA, then adds the OTP from the
            IPA reply to the manifest and creates instance in AWS.
        """
        hosts = []

        for _ in range(count):
            hostname = generate_hostname(domain=domain, role=role)
            ipa_host = self.ipaclient.enroll_ipa_host(ipa_cert_location=cert,
                                                      hostname=hostname)
            otp = ipa_host['result']['result']['randompassword']

            self.awsclient.create_instance(domain=domain,
                                           hostname=hostname,
                                           image_id=image_id,
                                           instance_type=instance_type,
                                           key=key,
                                           otp=otp,
                                           proxy=proxy,
                                           role=role,
                                           secgroup_ids=secgroup_ids,
                                           subnet_id=subnet_id)
            hosts.append(hostname)

        return hosts

    def delete_hosts(self, cert, hostnames):
        """ Unenrolls hosts from IPA and AWS """

        for hostname in hostnames:
            self.ipaclient.unenroll_ipa_host(ipa_cert_location=cert,
                                             hostname=hostname)
            self.awsclient.delete_instance(hostname=hostname)
        return hostnames

    def find_hosts(self, cert, pattern=''):
        """ Returns list of matching hosts from IPA.
            If no pattern is provided, returns all hosts.
        """
        return self.ipaclient.get_ipa_hosts(ipa_cert_location=cert,
                                            pattern=pattern)
