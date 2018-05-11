"""Runs IPA keytab service.
"""

# runs as root on an IPA server
# - uses host keytab for gss_accept_sec_context (gssapiprotocol service)
# - uses host keytab to obtain TGT for host/$hostname
#   - TGT is then used to run ipa service-add
#   - how does host/$hostname get "ipa service-add privs"?
# todo:
# - refresh TGT (or handle externally, tbd)
# - rework code (and underlying privs) to allow code to run as non-root (tbd)
# - rework error/exception handling
# - rework use of os.system

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import click

from treadmill_aws import ipakeytab

_LOGGER = logging.getLogger(__name__)


def init():
    """Top level command handler."""

    @click.command()
    @click.option('--port',
                  required=True,
                  type=int,
                  help='service port to listen on')
    @click.option('--realm',
                  required=False,
                  help='realm')
    def ipakeytabserver(port, realm):
        """Run IPA keytab daemon."""
        ipakeytab.run_server(port, realm)

    return ipakeytabserver
