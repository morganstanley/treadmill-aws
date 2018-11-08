"""AWS specific treadmill garbage collector
"""

import logging

from treadmill import admin
from treadmill import context
from treadmill_aws.awscontext import GLOBAL

_LOGGER = logging.getLogger(__name__)


class LDAP:
    """LDAP garbage collection"""
    @staticmethod
    def list():
        """List LDAP server records that are not valid ec2 instances"""
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
        return set(GLOBAL.ipaclient.get_hosts())

    @staticmethod
    def delete(hostname):
        """Delete an IPA server"""
        _LOGGER.info('removing %s from IPA', hostname)
        GLOBAL.ipaclient.unenroll_host(hostname=hostname)


__all__ = (
    'LDAP',
    'IPA'
)
