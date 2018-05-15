"""Implements AWS credential service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import logging

from twisted.internet import reactor
from twisted.internet import protocol

from treadmill import gssapiprotocol
from treadmill import utils
from treadmill_aws import awscontext

_LOGGER = logging.getLogger(__name__)
_DEFAULT_DURATION_SEC = 43200


# Disable warning for too many branches.
# pylint: disable=R0912
def run_server(port, accountid, adminprinc, realm):
    """Runs ipa keytab server."""
    _LOGGER.info(
        'AWS Credential server starting - listening on port %d',
        port)

    # no __init__ method.
    #
    # pylint: disable=W0232

    # pylint: disable=W0613
    def _error_str(self, string):
        return str("ERROR: %s" % string).encode("utf-8")

    class AWSCredentialServer(gssapiprotocol.GSSAPILineServer):
        """AWS Credential server."""

        def __init__(self, accountid, adminprinc):
            self.accountid = accountid
            self.adminprinc = adminprinc
            gssapiprotocol.GSSAPILineServer.__init__(self)

        def _validate_request(self, request):

            # should be a valid IAM role (for now)
            # but it will fail downstream if it is not
            # should probably verify character set and length
            pass

        def _authorize(self, requestor, request):

            if requestor == self.adminprinc:
                return

            if '@' not in requestor:
                _LOGGER.error((
                    'Internal error - expected requestor to be an kerberos'
                    'principal name, e.g., user@realm, got [%s]'), requestor)
                raise ValueError('Internal error')

            requestor_parts = requestor.split("@")
            request_parts = request.split("@")

            if requestor_parts[0] != request_parts[0]:
                raise ValueError((
                    'Requestor [%s] is not authorized to request credential'
                    'for role [%s]') % (requestor, request))

            if requestor_parts[1] != self.realm:
                raise ValueError(
                    'Requestor [%s] must be in authorized realm [%s]' %
                    (requestor, self.realm))

        def _get_credential(self, requestor, role, lifetime):

            actual_lifetime = min(lifetime, _DEFAULT_DURATION_SEC)

            sts = awscontext.GLOBAL.sts
            role_cred = sts.assume_role(
                RoleArn='arn:aws:iam::%s:role/%s' % (self.accountid, role),
                RoleSessionName=requestor,
                DurationSeconds=actual_lifetime)

            credential = {}
            credential['Credentials'] = role_cred['Credentials']
            credential['Credentials']['Expiration'] = \
                role_cred['Credentials']['Expiration'].isoformat()
            credential['AssumedRoleUser'] = role_cred['AssumedRoleUser']
            return credential

        @utils.exit_on_unhandled
        def got_line(self, data):
            """Process AWS credential request.
            """

            requestor = self.peer()
            role = data.decode()
            lifetime = self.peercred_lifetime()
            _LOGGER.info(
                'Processing AWS credential request for [%s] from [%s]',
                role,
                requestor)

            try:
                self._validate_request(role)
                self._authorize(requestor, role)
                credential = self._get_credential(requestor, role, lifetime)
                response = {}
                response['status'] = "success"
                response['response'] = credential
            except ValueError as exc:
                _LOGGER.error(repr(exc))
                response = {}
                response['status'] = "failure"
                response['response'] = {'why': str(exc)}
            except Exception:  # pylint: disable=W0703
                # could be authz error (including if role is not defined)
                # could be lifetime error is role does not have proper max
                _LOGGER.exception('Unknown exception')
                response = {}
                response['status'] = "failure"
                response['response'] = {'why': "internal server error"}

            response_string = json.dumps(response)
            self.write(response_string.encode("utf-8"))
            self.transport.loseConnection()

    class AWSCredentialServerFactory(protocol.Factory):
        """AWSCredentialServer factory."""

        def __init__(self, accountid, adminprinc, realm):
            protocol.Factory.__init__(self)
            self.accountid = accountid
            self.adminprinc = adminprinc
            self.realm = realm

        def buildProtocol(self, addr):  # pylint: disable=C0103
            return AWSCredentialServer(self.accountid, self.adminprinc)

    reactor.listenTCP(
        port, AWSCredentialServerFactory(
            accountid, adminprinc, realm))
    reactor.run()
