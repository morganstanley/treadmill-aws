"""Implements AWS credential service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import json
import logging
import re

import botocore

from twisted.internet import reactor
from twisted.internet import protocol

from treadmill import gssapiprotocol
from treadmill import utils
from treadmill_aws import awscontext

_LOGGER = logging.getLogger(__name__)
_DEFAULT_DURATION_SEC = 43200


def run_server(port, realm):
    """Runs AWS Credential server."""
    # TODO: pylint complains the function is too long, need to refactor.
    #
    # pylint: disable=R0915
    _LOGGER.info(
        'AWS Credential server starting - listening on port %d',
        port)

    def _parse_name(princ):
        match = re.search('^([^/@]*)/?([^@]*)@?(.*)$', princ)
        if match is None:
            _LOGGER.error((
                'Internal error - expected name to be a kerberos '
                'principal name, got [%s]'), princ)
            raise ValueError('Internal error')

        name = match.group(1)
        inst = match.group(2)
        realm = match.group(3)

        return [name, inst, realm]

    class AWSCredentialServer(gssapiprotocol.GSSAPILineServer):
        """AWS Credential server."""

        def __init__(self, realm):
            sts = awscontext.GLOBAL.sts
            self.realm = realm
            self.account_id = sts.get_caller_identity().get('Account')
            self.iamuser = sts.get_caller_identity().get('Arn')
            gssapiprotocol.GSSAPILineServer.__init__(self)

        def _validate_request(self, request):

            # as per "Limitations on IAM Entities and Objects"
            pattern = r'^[a-zA-Z0-9+=,.@_-]{1,64}$'
            match = re.search(pattern, request)
            if not match:
                raise ValueError("name [%s] does not meet character "
                                 "restrictions for IAM role" % request)

        def _authorize(self, requestor, request):

            requestor_name, requestor_inst, requestor_realm = \
                _parse_name(requestor)

            request_name, request_inst, request_realm = \
                _parse_name(request)

            if requestor_name != request_name:
                raise ValueError((
                    'Requestor [%s] is not authorized to request credential '
                    'for user [%s]') % (requestor, request))

            if requestor_realm not in self.realm:
                raise ValueError(
                    'Requestor [%s] is not in authorized realm [%s]' %
                    (requestor, self.realm))

            _LOGGER.info(
                'AWS credential request for [%s] from [%s]: authorized',
                request,
                requestor)

        def _get_credential(self, requestor, role, lifetime):

            actual_lifetime = min(lifetime, _DEFAULT_DURATION_SEC)

            sts = awscontext.GLOBAL.sts
            role_cred = sts.assume_role(
                RoleArn='arn:aws:iam::%s:role/%s' % (self.account_id, role),
                RoleSessionName=requestor,
                DurationSeconds=actual_lifetime)

            credential = {}
            credential['Credentials'] = role_cred['Credentials']
            credential['Credentials']['Expiration'] = \
                role_cred['Credentials']['Expiration'].isoformat()
            credential['AssumedRoleUser'] = role_cred['AssumedRoleUser']
            credential['Profile'] = '%s/%s' % (role, requestor)
            return credential

        @utils.exit_on_unhandled
        def got_line(self, data):
            """Process AWS credential request.
            """

            requestor = self.peer()
            request = data.decode()
            lifetime = self.peercred_lifetime()
            _LOGGER.info(
                'AWS credential request for [%s] from [%s]: received',
                request,
                requestor)

            try:
                self._validate_request(request)
                self._authorize(requestor, request)
                credential = self._get_credential(requestor, request, lifetime)
                response = {}
                response['status'] = "success"
                response['result'] = credential
                _LOGGER.info(
                    'AWS credential request for [%s] from [%s]: successful',
                    request,
                    requestor)
            except botocore.exceptions.ClientError as err:
                code = err.response['Error']['Code']
                msg = err.response['Error']['Message']
                _LOGGER.error(err)
                _LOGGER.error('sts.assume_role(%s) by [%s] failed: [%s]',
                              request, self.iamuser, code)
                response = {}
                response['status'] = "failure"
                response['result'] = {'why': "internal server error"}
            except ValueError as err:
                _LOGGER.error(err)
                response = {}
                response['status'] = "failure"
                response['result'] = {'why': str(err)}
            except Exception as err:  # pylint: disable=W0703
                # could be authz error (including if role is not defined)
                # could be lifetime error is role does not have proper max
                _LOGGER.exception('Unknown exception')
                response = {}
                response['status'] = "failure"
                response['result'] = {'why': "internal server error"}

            response_string = json.dumps(response)
            self.write(response_string.encode("utf-8"))
            self.transport.loseConnection()

    class AWSCredentialServerFactory(protocol.Factory):
        """AWSCredentialServer factory."""

        def __init__(self, realm):
            protocol.Factory.__init__(self)
            self.realm = realm

        def buildProtocol(self, addr):
            return AWSCredentialServer(self.realm)

    reactor.listenTCP(port, AWSCredentialServerFactory(realm))
    reactor.run()
