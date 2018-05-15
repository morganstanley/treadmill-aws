"""Implements IPA keytab service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import io
import logging
import pwd
import os
import re
import shutil
import tempfile

from twisted.internet import reactor
from twisted.internet import protocol

from treadmill import gssapiprotocol
from treadmill import utils

_LOGGER = logging.getLogger(__name__)


def run_server(port, realm):
    """Runs ipa keytab server."""
    _LOGGER.info('IPA Keytab server starting - listening on port %d', port)

    # no __init__ method.
    #
    # pylint: disable=W0232

    def _error_str(string):
        return str("ERROR: %s" % string).encode("utf-8")

    class IPAKeytabServer(gssapiprotocol.GSSAPILineServer):
        """IPA Keytab server."""

        def __init__(self, realm):
            self.realm = realm
            gssapiprotocol.GSSAPILineServer.__init__(self)

        def _validate_request(self, username):

            if username == "admin" \
                    or username == "host" \
                    or username == "root":
                raise ValueError(
                    'keytabs for \'%s\' are not supported' %
                    username)

            try:
                uid = pwd.getpwnam(username)
            except KeyError:
                raise KeyError("%s is not a valid username" % username)
            except BaseException:
                raise

        def _validate_requestor(self, requestor):

            match = re.search('^(.*)/(.*)@(.*)$', requestor)
            if match is None:
                raise ValueError(
                    'Requestor %s must be a host service principal' %
                    requestor)

            requestor_name = match.group(1)
            requestor_inst = match.group(2)
            requestor_realm = match.group(3)

            if requestor_name != "host":
                raise ValueError(
                    'Requestor %s is not a host principal' % requestor)

            if self.realm is not None \
                    and requestor_realm != self.realm:
                raise ValueError(
                    'Requestor \'%s\' must be in authorized realm \'%s\'' %
                    (requestor, self.realm))

            return (match.group(1), match.group(2), match.group(3))

        def _get_keytab(self, name, inst, realm):
            tmpktdir = tempfile.mkdtemp(prefix="ipakeytab-")
            tmpkt = "%s/%s" % (tmpktdir, name)
            service = "%s/%s@%s" % (name, inst, realm)

            _LOGGER.info(
                "writing keytab for %s/%s@%s => %s",
                name,
                inst,
                realm,
                tmpkt)

            os.system(
                "kadmin.local ktadd -k %s -norandkey %s" %
                (tmpkt, service))
            if not os.path.isfile(tmpkt):
                os.system("klist -5 > /tmp/klist.out")
                _LOGGER.info("running: ipa service-add %s", service)
                os.system("ipa service-add %s" % service)
                os.system("kadmin.local cpw -randkey %s" % service)
                os.system(
                    "kadmin.local ktadd -k %s -norandkey %s" %
                    (tmpkt, service))

            if os.path.isfile(tmpkt):
                with io.open(tmpkt, 'rb') as f:
                    retval = base64.standard_b64encode(f.read())
            else:
                retval = _error_str(
                    "unable to generate keytab for %s/%s@%s" %
                    (name, inst, realm))

            shutil.rmtree(tmpktdir)
            return retval

        @utils.exit_on_unhandled
        def got_line(self, data):
            """Process ipakeytab request.

            - requestor_princ must be host principal (host/$hostname)
            - [requested username must be for container running on $hostname
            - generate keytab for $username/$hostname
            - send back generated keytab
            """

            requestor_princ = self.peer()
            username = data.decode()
            _LOGGER.info(
                'Processing ipakeytab request for \'%s\' from \'%s\'',
                username,
                requestor_princ)

            try:
                self._validate_request(username)
                requestor = self._validate_requestor(requestor_princ)
                req_name = requestor[0]
                req_inst = requestor[1]
                req_realm = requestor[2]
                keytab_entries = self._get_keytab(
                    username, req_inst, req_realm)
            except Exception as err:  # pylint: disable=W0703
                _LOGGER.error(repr(err))
                response = "ERROR: " + str(err)
                self.write(str(response).encode("utf-8"))
                return

            self.write(keytab_entries)
            self.transport.loseConnection()

    class IPAKeytabServerFactory(protocol.Factory):
        """IPAKeytabServer factory."""

        def __init__(self, realm):
            protocol.Factory.__init__(self)
            self.realm = realm

        def buildProtocol(self, addr):  # pylint: disable=C0103
            return IPAKeytabServer(self.realm)

    if 'KRB5_KTNAME' in os.environ:
        del os.environ['KRB5_KTNAME']
    # todo - use some flavor of mktemp
    # refresh this periodically
    os.environ['KRB5CCNAME'] = "FILE:/tmp/krb5cc_root_ipakeytabd"
    os.system("kinit -k")

    reactor.listenTCP(port, IPAKeytabServerFactory(realm))
    reactor.run()
