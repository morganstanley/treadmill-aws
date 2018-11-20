"""AWS specific treadmill garbage collector
"""

import logging

from treadmill import admin
from treadmill import context
from treadmill_aws.awscontext import GLOBAL

_LOGGER = logging.getLogger(__name__)
_ACCOUNT = GLOBAL.iam.list_account_aliases().get('AccountAliases').pop()


class LDAP:
    """LDAP garbage collection"""
    @staticmethod
    def list():
        """List LDAP server records that are not valid ec2 instances"""
        _LOGGER.info('fetched server list from LDAP')
        client = admin.Server(context.GLOBAL.ldap.conn)
        return {host.get("_id") for host in client.list({})}

    @staticmethod
    def delete(hostname):
        """Delete a LDAP server record"""
        _LOGGER.info('removing %s from LDAP', hostname)
        admin.Server(context.GLOBAL.ldap.conn).delete(hostname)


class IPA:
    """IPA garbage collection"""
    @staticmethod
    def list():
        """List IPA server records that are not valid ec2 instances"""
        _LOGGER.info('fetched server list from IPA')
        return set(GLOBAL.ipaclient.get_hosts(nshostlocation=_ACCOUNT))

    @staticmethod
    def delete(hostname):
        """Delete an IPA server"""
        _LOGGER.info('removing %s from IPA', hostname)
        GLOBAL.ipaclient.unenroll_host(hostname=hostname)


__all__ = (
    'LDAP',
    'IPA'
)
