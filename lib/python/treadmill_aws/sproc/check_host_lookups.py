"""Check host lookups."""

import logging
import time

import click
import dns

from treadmill import context
from treadmill import dnsutils
from treadmill import sysinfo


_LOGGER = logging.getLogger(__name__)

_DEFAULT_INTERVAL = 60


# FIXME: Move to treadmill.dnsutils.
def _ptr(ip_address, dns_server=None):
    reversename = dns.reversename.from_address(ip_address)
    answer = dnsutils.query(reversename, dns.rdatatype.PTR, dns_server)
    return [str(rec) for rec in answer]


def _check(hostname, dns_domain):
    nameservers = dnsutils.ns(dns_domain)
    for ns in nameservers:
        _LOGGER.info('Name server: %s', ns)
        dns_server = ([ns], None)

        a_records = dnsutils.a(hostname, dns_server)
        _LOGGER.info('A records for %s: %r', hostname, a_records)
        assert len(a_records) == 1

        ip_address = a_records[0]

        ptr_records = _ptr(ip_address)
        _LOGGER.info('PTR records for %s: %r', ip_address, ptr_records)
        assert len(ptr_records) == 1

        ptr_hostname = ptr_records[0]
        if ptr_hostname.endswith('.'):
            ptr_hostname = ptr_hostname[:-1]

        if hostname != ptr_hostname:
            _LOGGER.error('%s != %s', hostname, ptr_hostname)
            return False
    return True


def init():
    """Check host lookups."""

    @click.command()
    @click.option(
        '--interval', required=False, default=_DEFAULT_INTERVAL, type=int,
        help='Time interval between checks (seconds).'
    )
    def run(interval):
        hostname = sysinfo.hostname()
        dns_domain = context.GLOBAL.dns_domain

        while True:
            _LOGGER.info('Checking host lookups: %s, %s', hostname, dns_domain)
            try:
                if not _check(hostname, dns_domain):
                    _LOGGER.error('Check failed - exiting.')
                    return
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception('Error while checking host lookups: %r', err)
            time.sleep(interval)

    return run
