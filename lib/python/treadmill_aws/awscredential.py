"""Implements AWS credential service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import grp
import json
import logging
import pwd
import re

from twisted.internet import reactor
from twisted.internet import protocol

from treadmill import gssapiprotocol
from treadmill import utils
from treadmill_aws import awscontext

_LOGGER = logging.getLogger(__name__)
_DEFAULT_DURATION_SEC = 43200


def run_server(port, account_id, admin_group, realm):
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

        def __init__(self, account_id, admin_group, realm):
            self.account_id = account_id
            self.admin_group = admin_group
            self.realm = realm
            gssapiprotocol.GSSAPILineServer.__init__(self)

        def _validate_request(self, request):

            # should verify it is a valid IAM role
            # but it will fail downstream if it is not
            # for now we just validate that it is a valid user
            try:
                uid = pwd.getpwnam(request)
            except KeyError:
                raise ValueError("user [%s] is not defined" % request)

        def _authorize(self, requestor, request):

            # admin can request anything (hence request is not considered)
            if self._authorize_admin(requestor):
                return

            self._authorize_self(requestor, request)

        def _authorize_admin(self, requestor):

            if admin_group is None:
                return False

            requestor_name, requestor_inst, requestor_realm = \
                _parse_name(requestor)

            try:
                if requestor_name in grp.getgrnam(self.admin_group).gr_mem \
                        and requestor_inst == '' \
                        and requestor_realm == self.realm:
                    return True
            except KeyError as err:
                _LOGGER.warning(
                    'admin group [%s] does not exist', self.admin_group)

            return False

        def _authorize_self(self, requestor, request):

            requestor_name, requestor_inst, requestor_realm = \
                _parse_name(requestor)

            request_name, request_inst, request_realm = \
                _parse_name(request)

            if requestor_name != request_name:
                raise ValueError((
                    'Requestor [%s] is not authorized to request credential '
                    'for user [%s]') % (requestor, request))

            if requestor_realm != self.realm:
                raise ValueError(
                    'Requestor [%s] is not in authorized realm [%s]' %
                    (requestor, self.realm))

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
                'Processing AWS credential request for [%s] from [%s]',
                request,
                requestor)

            try:
                self._validate_request(request)
                self._authorize(requestor, request)
                credential = self._get_credential(requestor, request, lifetime)
                response = {}
                response['status'] = "success"
                response['result'] = credential
            except ValueError as err:
                _LOGGER.error(repr(err))
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

        def __init__(self, account_id, admin_group, realm):
            protocol.Factory.__init__(self)
            self.account_id = account_id
            self.admin_group = admin_group
            self.realm = realm

        def buildProtocol(self, addr):
            return AWSCredentialServer(self.account_id,
                                       self.admin_group,
                                       self.realm)

    reactor.listenTCP(
        port, AWSCredentialServerFactory(
            account_id, admin_group, realm))
    reactor.run()
