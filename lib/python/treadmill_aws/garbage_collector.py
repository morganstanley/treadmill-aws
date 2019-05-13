"""AWS specific garbage collector plugins."""

import logging

from treadmill import context
from treadmill.admin import exc as admin_exceptions

from treadmill_aws import awscontext
from treadmill_aws import ipaclient


_LOGGER = logging.getLogger(__name__)

# FIXME: Use aws_account from the cell data instead.
_ACCOUNT = awscontext.GLOBAL.iam.list_account_aliases().get(
    'AccountAliases'
).pop()


class LDAP:
    """LDAP garbage collection plugin."""

    @staticmethod
    def list():
        """List servers in LDAP."""
        _LOGGER.info('Fetching server list from LDAP')
        admin_srv = context.GLOBAL.admin.server()
        return {server.get("_id") for server in admin_srv.list({})}

    @staticmethod
    def delete(hostname):
        """Delete server from LDAP."""
        _LOGGER.info('Deleting %s from LDAP', hostname)
        try:
            context.GLOBAL.admin.server().delete(hostname)
        except admin_exceptions.NoSuchObjectResult:
            _LOGGER.info('Error deleting %s from LDAP: NoSuchObject', hostname)


class IPA:
    """IPA garbage collection plugin."""

    @staticmethod
    def list():
        """List servers in IPA."""
        _LOGGER.info('Fetching server list from IPA')
        ipa_client = awscontext.GLOBAL.ipaclient
        return set(ipa_client.list_hosts(nshostlocation=_ACCOUNT))

    @staticmethod
    def delete(hostname):
        """Delete server from IPA."""
        _LOGGER.info('Deleting %s from IPA', hostname)
        try:
            awscontext.GLOBAL.ipaclient.unenroll_host(hostname)
        except ipaclient.NotFoundError:
            _LOGGER.info('Error deleting %s from IPA: NotFoundError', hostname)


class DNS:
    """DNS garbage collection plugin."""

    @staticmethod
    def list():
        """List servers in DNS."""
        cell = context.GLOBAL.cell
        ipa_client = awscontext.GLOBAL.ipaclient
        ipa_domain = awscontext.GLOBAL.ipa_domain

        # Consider only records that begin with the cell name.
        prefix = '{}-'.format(cell)
        servers = {}

        # Check records in the forward zone.
        dns_records = ipa_client.list_dns_records()
        for dns_record in dns_records:
            idnsname = dns_record['idnsname'][0]
            hostname = '{}.{}'.format(idnsname, ipa_domain)
            if hostname.startswith(prefix):
                servers[hostname] = None

        # Check records in all reverse zones.
        reverse = {}
        dns_zones = ipa_client.list_dns_zones('.in-addr.arpa.')
        for dns_zone in dns_zones:
            zone_name = dns_zone['idnsname'][0]
            dns_records = ipa_client.list_dns_records(dns_zone=zone_name)
            for dns_record in dns_records:
                idnsname = dns_record['idnsname'][0]
                if 'ptrrecord' not in dns_record:
                    continue
                ptrrecord = dns_record['ptrrecord'][0]
                hostname = ptrrecord
                if hostname.endswith('.'):
                    hostname = hostname[:-1]
                if ((hostname.startswith(prefix) and
                     hostname.endswith(ipa_domain))):
                    servers[hostname] = (idnsname, zone_name, ptrrecord)

        return servers

    @staticmethod
    def delete(hostname, reverse_record=None):
        """Delete server from DNS."""
        _LOGGER.info('Deleting %s from DNS: %r', hostname, reverse_record)
        ipa_client = awscontext.GLOBAL.ipaclient
        ipa_domain = awscontext.GLOBAL.ipa_domain

        idnsname = hostname.split('.')[0]
        try:
            ipa_client.force_delete_dns_record(idnsname, dns_zone=ipa_domain)
        except ipaclient.NotFoundError:
            _LOGGER.info('Error deleting %s from DNS: NotFoundError', idnsname)

        if not reverse_record:
            return

        idnsname, zone_name, ptrrecord = reverse_record
        try:
            ipa_client.delete_ptr_record(
                idnsname, ptrrecord, zone_name
            )
        except (ipaclient.ExecutionError, ipaclient.NotFoundError) as err:
            _LOGGER.info('Error deleting %r from DNS: %r', reverse_record, err)


__all__ = (
    'LDAP',
    'IPA',
    'DNS',
)
