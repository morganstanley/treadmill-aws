"""Global AWS context."""

import boto3

from treadmill import context

from treadmill_aws import ipaclient


class AWSContext(object):
    """Global AWS context for handling AWS sessions."""

    __slots__ = (
        'region_name',
        'ipa_certs',
        '_ipa_domain',
        '_session',
        '_ipaclient',
    )

    def __init__(self):
        self._session = None
        self._ipaclient = None
        self._ipa_domain = None
        self.ipa_certs = None
        self.region_name = None

    @property
    def session(self):
        """Lazily establishes AWS session.
        """
        if self._session:
            return self._session

        self._session = boto3.Session(region_name=self.region_name)
        return self._session

    @property
    def ec2(self):
        """Returns EC2 resource manager."""
        return self.session.client('ec2')

    @property
    def s3(self):
        """Returns S3 resource manager."""
        return self.session.client('s3')

    @property
    def iam(self):
        """Returns IAM resource manager."""
        return self.session.client('iam')

    @property
    def sts(self):
        """Returns STS resource manager."""
        return self.session.client('sts')

    @property
    def ipaclient(self):
        """Lazily creates IPA client.
        """
        if self._ipaclient:
            return self._ipaclient

        self._ipaclient = ipaclient.IPAClient(certs=self.ipa_certs,
                                              domain=self.ipa_domain)
        return self._ipaclient

    @property
    def ipa_domain(self):
        """Returns IPA domain."""
        if not self._ipa_domain:
            self._ipa_domain = context.GLOBAL.dns_domain

        return self._ipa_domain

    @ipa_domain.setter
    def ipa_domain(self, value):
        """IPA domain, setter.
        """
        self._ipa_domain = value


GLOBAL = AWSContext()
