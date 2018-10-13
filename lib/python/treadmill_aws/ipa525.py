"""Implements IPA525 credential service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import grp
import io
import logging
import json
import os
import pwd
import re
import shutil
import tempfile

from twisted.internet import reactor
from twisted.internet import protocol

from treadmill import gssapiprotocol
from treadmill import utils

_LOGGER = logging.getLogger(__name__)


# Disable warning for too many branches.
# pylint: disable=R0912
def run_server(port, client_realm, server_realm, admin_group):
    """Runs IPA525 server."""
    # TODO: pylint complains the function is too long, need to refactor.
    #
    # pylint: disable=R0915
    _LOGGER.info(
        'IPA 525 server starting - listening on port %d',
        port)

    def _parse_name(princ):
        match = re.search('^([^/@]*)/?([^@]*)@?(.*)$', princ)
        if match is None:
            _LOGGER.error(
                'Internal error - expected name to be a kerberos '
                'principal name, got [%s]', princ)
            raise ValueError('Internal error')

        name = match.group(1)
        inst = match.group(2)
        realm = match.group(3)

        return [name, inst, realm]

    class IPA525Server(gssapiprotocol.GSSAPILineServer):
        """IPA525 server."""

        def __init__(self, client_realm, server_realm, admin_group):
            gssapiprotocol.GSSAPILineServer.__init__(self)
            self.client_realm = client_realm
            self.server_realm = server_realm
            self.admin_group = admin_group

        def _validate_request(self, request):
            name, inst, realm = _parse_name(request)

            if inst:
                raise ValueError(
                    'Request [%s] is for a service principal - not supported' %
                    request)

            if realm:
                if realm != self.server_realm:
                    raise ValueError(
                        'Request [%s] is for principal in an unsupported '
                        'service realm [%s]' % (request, realm))

            try:
                uid = pwd.getpwnam(name)
            except KeyError:
                raise KeyError("%s is not a valid username" % name)

        def _authorize(self, requestor, request):

            if self._authorize_admin(requestor):
                return

            self._authorize_self(requestor, request)

        def _authorize_admin(self, requestor):

            if self.admin_group is None:
                return False

            requestor_name, requestor_inst, requestor_realm = \
                _parse_name(requestor)

            try:
                if requestor_name in grp.getgrnam(self.admin_group).gr_mem \
                        and requestor_inst == '' \
                        and requestor_realm == self.server_realm:
                    return True
            except KeyError as err:
                _LOGGER.warning(
                    'admin group [%s] does not exist', self.admin_group)

            return False

        def _authorize_self(self, requestor, request):
            requestor_name, requestor_inst, requestor_realm = \
                _parse_name(requestor)
            request_name, request_inst, request_realm = _parse_name(request)

            if requestor_name != request_name:
                raise ValueError(
                    'Requestor [%s] is not authorized to request tickets for '
                    '[%s] - userid mismatch' % (requestor, request))

            if request_inst:
                raise ValueError(
                    'Request [%s] is for service principal - not supported' %
                    request)

            if requestor_realm not in self.client_realm:
                raise ValueError(
                    'Requestor [%s] is not authorized to request ticket for '
                    '[%s] - requestor is from an unauthorized realm' %
                    (requestor, request))

        def _get_ticket(self, request, lifetime):
            name, inst, realm = _parse_name(request)
            tmpdir = tempfile.mkdtemp(prefix="ipa525-")
            tmpkt = "%s/%s.keytab" % (tmpdir, name)
            tmpcc = "%s/%s.ticket" % (tmpdir, name)

            _LOGGER.info(
                "obtaining ticket for [%s] to tmp ticket file %s",
                request, tmpcc)

            os.system(
                "kadmin.local ktadd -k %s -norandkey %s" %
                (tmpkt, request))

            if not os.path.isfile(tmpkt) and inst:
                _LOGGER.error("unable to extract keytab for %s", request)
                raise ValueError('Internal error')

            os.system(
                "kinit -l %ds -k -t %s -c %s %s" %
                (lifetime, tmpkt, tmpcc, request))

            if os.path.isfile(tmpcc):
                with io.open(tmpcc, 'rb') as f:
                    response = base64.standard_b64encode(f.read()).decode()
            else:
                _LOGGER.error("unable to generate ticket for %s", request)
                raise ValueError('Internal error')

            shutil.rmtree(tmpdir)
            return response

        @utils.exit_on_unhandled
        def got_line(self, data):
            """Process IPA525 credential request.
            """

            requestor = self.peer()
            request = data.decode()
            lifetime = self.peercred_lifetime()
            _LOGGER.info(
                'Processing IPA525 credential request [%s] from [%s]',
                request,
                requestor)

            try:
                self._validate_request(request)
                self._authorize(requestor, request)
                ticket = self._get_ticket(request, lifetime)
                response = {}
                response['status'] = "success"
                result = {}
                result['principal'] = request
                result['lifetime'] = lifetime
                result['credential'] = ticket
                response['result'] = result
            except ValueError as err:
                _LOGGER.error(repr(err))
                response = {}
                response['status'] = "failure"
                response['result'] = {'why': str(err)}
            except Exception:  # pylint: disable=W0703
                _LOGGER.exception('Unknown exception')
                response = {}
                response['status'] = "failure"
                response['result'] = {'why': "internal server error(1)"}
                raise

            response_string = json.dumps(response)
            self.write(response_string.encode("utf-8"))
            self.transport.loseConnection()

    class IPA525ServerFactory(protocol.Factory):
        """IPA525Server factory."""

        def __init__(self, client_realm, server_realm, admin_group):
            protocol.Factory.__init__(self)
            self.client_realm = client_realm
            self.server_realm = server_realm
            self.admin_group = admin_group

        def buildProtocol(self, addr):  # pylint: disable=C0103
            return IPA525Server(self.client_realm,
                                self.server_realm,
                                self.admin_group)

    reactor.listenTCP(
        port, IPA525ServerFactory(
            client_realm, server_realm, admin_group))
    reactor.run()
