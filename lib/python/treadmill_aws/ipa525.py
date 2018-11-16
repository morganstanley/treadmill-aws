"""Implements IPA525 credential service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import io
import logging
import json
import http.client
import os
import pwd
import re
import shutil
import tempfile

from twisted.internet import reactor
from twisted.internet import protocol

from treadmill import authz
from treadmill import gssapiprotocol
from treadmill import utils

_LOGGER = logging.getLogger(__name__)


def _parse_name(princ):
    """Parse Kerberos principal, return tuple of name, instance, realm."""
    match = re.search('^([^/@]*)/?([^@]*)@?(.*)$', princ)
    if match is None:
        _LOGGER.error(
            'Internal error - expected name to be a kerberos '
            'principal name, got [%s]', princ)
        raise ValueError('Internal error')

    name = match.group(1)
    inst = match.group(2)
    realm = match.group(3)

    return name, inst, realm


class IPA525Server(gssapiprotocol.GSSAPILineServer):
    """IPA525 server."""

    def __init__(self, client_realm, server_realm, authz_remote):
        gssapiprotocol.GSSAPILineServer.__init__(self)
        self.client_realm = client_realm
        self.server_realm = server_realm
        self.authorizer = None
        if authz_remote:
            self.authorizer = authz.ClientAuthorizer(self.peer,
                                                     authz_remote)

    def _validate(self, request):
        """Validate request, raises ValueError on failure.

        - instance must be empty.
        - realm must match that of the server.
        - name must be existing uid.
        """
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
            raise ValueError("%s is not a valid username" % name)

    def _authorize(self, requestor, request):
        """Authorizes request.

        - Client realm must be trusted.
        - Client instance must be empty.
        - If name of the client same as of the ticket requested, authorize.
        - Otherwise, consult authorization service if configured.

        Raises authz.AuthorizationError if not authorized.
        """
        requestor_name, requestor_inst, requestor_realm = \
            _parse_name(requestor)

        if requestor_realm not in self.client_realm:
            raise authz.AuthorizationError([
                'Untrusted client realm: {}.'.format(requestor_realm)
            ])
        if requestor_inst:
            raise authz.AuthorizationError([
                'Request from service principal, not supported.'
            ])

        # We already validated request, only interested in the name.
        request_name, _request_inst, _request_realm = _parse_name(request)

        # Authorize self.
        if request_name == requestor_name:
            return

        # This is impersonation request. If authorizer is configure,
        # consult it (it will raise if not authorized), else deny.
        if self.authorizer:
            self.authorizer.authorize(
                'user', 'ipa525', [request_name, None], None
            )
        else:
            raise authz.AuthorizationError(['Not authorized.'])

    def _get_ticket(self, request, lifetime):
        name, inst, realm = _parse_name(request)
        tmpdir = tempfile.mkdtemp(prefix='ipa525-')
        tmpkt = '%s/%s.keytab' % (tmpdir, name)
        tmpcc = '%s/%s.ticket' % (tmpdir, name)

        _LOGGER.info(
            'obtaining ticket for [%s] to tmp ticket file %s',
            request, tmpcc)

        os.system(
            'kadmin.local ktadd -k %s -norandkey %s' %
            (tmpkt, request))

        if not os.path.isfile(tmpkt) and inst:
            _LOGGER.error('unable to extract keytab for %s', request)
            raise ValueError('Internal error')

        os.system(
            'kinit -l %ds -k -t %s -c %s %s' %
            (lifetime, tmpkt, tmpcc, request))

        if os.path.isfile(tmpcc):
            with io.open(tmpcc, 'rb') as f:
                response = base64.standard_b64encode(f.read()).decode()
        else:
            _LOGGER.error('unable to generate ticket for %s', request)
            raise ValueError('Internal error')

        shutil.rmtree(tmpdir)
        return response

    def _process_request(self, request):
        """Process request, returns json response."""
        requestor = self.peer()
        lifetime = self.peercred_lifetime()
        _LOGGER.info(
            'Processing IPA525 credential request [%s] from [%s]',
            request,
            requestor)

        try:
            self._validate(request)
            self._authorize(requestor, request)
            ticket = self._get_ticket(request, lifetime)
            response = {
                'status': 'success',
                'code': http.client.OK,
                'result': {
                    'principal': request,
                    'lifetime': lifetime,
                    'credential': ticket,
                }
            }
        except ValueError as value_err:
            _LOGGER.error(repr(value_err))
            response = {
                'status': 'failure',
                'code': http.client.BAD_REQUEST,
                'result': {'why': str(value_err)},
            }
        except authz.AuthorizationError as auth_err:
            _LOGGER.info(str(auth_err))
            response = {
                'status': 'failure',
                'code': http.client.FORBIDDEN,
                'result': {'why': str(auth_err)},
            }
        except Exception as err:  # pylint: disable=W0703
            _LOGGER.exception('Unknown exception')
            response = {
                'status': 'failure',
                'code': http.client.INTERNAL_SERVER_ERROR,
                'result': {'why': 'internal server error: {}'.format(err)},
            }

        return response

    @utils.exit_on_unhandled
    def got_line(self, data):
        """Process IPA525 credential request.
        """
        request = data.decode()
        response = self._process_request(request)
        response_string = json.dumps(response)
        self.write(response_string.encode('utf-8'))
        self.transport.loseConnection()


# Disable warning for too many branches.
# pylint: disable=R0912
def run_server(port, client_realm, server_realm, authz_remote):
    """Runs IPA525 server."""
    # TODO: pylint complains the function is too long, need to refactor.
    #
    # pylint: disable=R0915
    _LOGGER.info(
        'IPA 525 server starting - listening on port %d',
        port)

    class IPA525ServerFactory(protocol.Factory):
        """IPA525Server factory."""

        def __init__(self, client_realm, server_realm, authz_remote):
            protocol.Factory.__init__(self)
            self.client_realm = client_realm
            self.server_realm = server_realm
            self.authz_remote = authz_remote

        def buildProtocol(self, addr):  # pylint: disable=C0103
            return IPA525Server(self.client_realm,
                                self.server_realm,
                                self.authz_remote)

    reactor.listenTCP(
        port, IPA525ServerFactory(
            client_realm, server_realm, authz_remote))
    reactor.run()
