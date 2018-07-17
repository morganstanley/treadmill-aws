"""Implements IPA keytab service.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import grp
import io
import json
import logging
import pwd
import os
import re
import shutil
import socket
import tempfile

from twisted.internet import reactor
from twisted.internet import protocol

from treadmill import gssapiprotocol
from treadmill import utils

_LOGGER = logging.getLogger(__name__)
_SERVICE_BLACKLIST = ['admin', 'host', 'root']


def run_server(port, realm, admin_group):
    """Runs IPA keytab server."""
    # TODO: pylint complains the function is too long, need to refactor.
    #
    # pylint: disable=R0915
    _LOGGER.info('IPA Keytab server starting - listening on port %d', port)

    def _parse_name(princ):
        match = re.search('^([^/@]*)/?([^@]*)@?(.*)$', princ)
        if match is None:
            _LOGGER.error((
                'Internal error - expected name [%s] to be a kerberos'
                'principal name'), princ)
            raise ValueError('Internal error')

        name = match.group(1)
        inst = match.group(2)
        realm = match.group(3)

        return [name, inst, realm]

    class IPAKeytabServer(gssapiprotocol.GSSAPILineServer):
        """IPA Keytab server."""

        def __init__(self, realm, admin_group):
            gssapiprotocol.GSSAPILineServer.__init__(self)
            self.realm = realm
            self.admin_group = admin_group

        def _validate_request_service(self, request):
            name, inst, realm = _parse_name(request)
            if name in _SERVICE_BLACKLIST:
                raise ValueError(
                    'Request for [%s], keytabs for [%s] services are not'
                    'supported' % (request, name))

            try:
                uid = pwd.getpwnam(name)
            except KeyError:
                raise ValueError(
                    'Request for [%s], [%s] is not defined in IPA' %
                    (request, name))

            if inst == "localhost":
                raise ValueError(
                    'Request for [%s], [%s] is not considered a valid '
                    'host name for keytabs' % (request, inst))

            try:
                fqdn, aliases, ips = socket.gethostbyname_ex(inst)
            except socket.gaierror as err:
                raise ValueError(
                    'Request for [%s], hostname [%s] is not defined' %
                    (request, inst))

            if fqdn != inst:
                raise ValueError(
                    'Request for [%s], [%s] is not the fqdn for [%s]' %
                    (request, inst, fqdn))

        def _validate_request_user(self, request):
            name, inst, realm = _parse_name(request)
            try:
                uid = pwd.getpwnam(name)
            except KeyError:
                raise ValueError("%s is not a valid username" % name)

        def _validate_request(self, request):

            # request must be either $user or $user/$hostname

            if '@' in request:
                raise ValueError(
                    'Request [%s] may not include realm' % request)

            if '/' in request:
                self._validate_request_service(request)
            else:
                self._validate_request_user(request)

        def _authorize_service_request(self, requestor, request):
            requestor_name, requestor_inst, requestor_realm = \
                _parse_name(requestor)
            request_name, request_inst, request_realm = _parse_name(request)

            if requestor_name != "host":
                raise ValueError(
                    'Requestor [%s] is not a host principal' % requestor)

            if requestor_realm != self.realm:
                raise ValueError(
                    'Requestor [%s] must be in authorized realm [%s]' %
                    (requestor, self.realm))

            if requestor_inst != request_inst:
                raise ValueError(
                    'Hostname in request [%s] does not match hostname in '
                    'requestor principal [%s]' % (request, requestor))

        def _authorize_user_request(self, requestor, request):
            requestor_name, requestor_inst, requestor_realm = \
                _parse_name(requestor)
            request_name, request_inst, request_realm = _parse_name(request)

            if requestor_name != request_name:
                raise ValueError(
                    'Requestor [%s] is not authorized to request keytab for '
                    '[%s]' % (requestor, request))

            if requestor_realm != self.realm:
                raise ValueError(
                    'Requestor [%s] is not in authorized realm' % (requestor))

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

        def _authorize(self, requestor, request):

            # admin can request anything
            if self._authorize_admin(requestor):
                return

            # not admin, authorize based on request
            if '/' in request:
                # request is for service principal keytab
                self._authorize_service_request(requestor, request)
            else:
                # request is for user keytab
                self._authorize_user_request(requestor, request)

        def _get_keytab_entries(self, request):
            name, inst, realm = _parse_name(request)
            tmpktdir = tempfile.mkdtemp(prefix="ipakeytab-")
            tmpkt = "%s/%s" % (tmpktdir, name)

            _LOGGER.info(
                "writing keytab for [%s] to tmp keytab file %s",
                request, tmpkt)

            os.system(
                "kadmin.local ktadd -k %s -norandkey %s" %
                (tmpkt, request))
            if not os.path.isfile(tmpkt) and inst:
                # only do this part if request is for service principal
                _LOGGER.info("running: ipa service-add %s", request)
                os.system("klist -s || kinit -k")
                os.system("ipa service-add %s" % request)
                os.system("kadmin.local cpw -randkey %s" % request)
                os.system(
                    "kadmin.local ktadd -k %s -norandkey %s" %
                    (tmpkt, request))

            if os.path.isfile(tmpkt):
                with io.open(tmpkt, 'rb') as f:
                    kt_entries = base64.standard_b64encode(f.read()).decode()
            else:
                _LOGGER.error("unable to generate keytab for %s", request)
                raise ValueError('Internal error')

            shutil.rmtree(tmpktdir)
            return kt_entries

        @utils.exit_on_unhandled
        def got_line(self, data):
            """Process ipakeytab request.

            * if data is $user:
                - $user must already exist in IPA
                - requestor must be admin or $user
                - ipakeytab will generate keytab for $user
                - ipakeytab will send back generated keytab

            * if data is $user/$hostname
                - $user must already exist
                - $user must not be on blacklist
                - requestor must be admin or host/$hostname
                - ipakeytab will create $user/$hostname if needed
                - ipakeytab will generate keytab for $user/$hostname
                - ipakeytab will send back generated keytab
            """

            requestor = self.peer()
            request = data.decode()
            _LOGGER.info(
                'Processing ipakeytab request for [%s] from [%s]',
                request,
                requestor)

            try:
                self._validate_request(request)
                self._authorize(requestor, request)
                keytab_entries = self._get_keytab_entries(request)
                result = {}
                result['keytab_entries'] = keytab_entries
                result['principal'] = request
                response = {}
                response['status'] = "success"
                response['result'] = result
            except ValueError as err:
                _LOGGER.error(repr(err))
                result = {}
                result['why'] = str(err)
                result['principal'] = request
                response = {}
                response['status'] = "failure"
                response['result'] = result
            except Exception as err:  # pylint: disable=W0703
                _LOGGER.exception('Unknown exception')
                response = {}
                response['status'] = "failure"
                response['result'] = {'why': "internal server error"}

            response_string = json.dumps(response)
            self.write(response_string.encode('utf-8'))
            self.transport.loseConnection()

    class IPAKeytabServerFactory(protocol.Factory):
        """IPAKeytabServer factory."""

        def __init__(self, realm, admin_group):
            protocol.Factory.__init__(self)
            self.realm = realm
            self.admin_group = admin_group

        def buildProtocol(self, addr):  # pylint: disable=C0103
            return IPAKeytabServer(self.realm, self.admin_group)

    if 'KRB5_KTNAME' in os.environ:
        del os.environ['KRB5_KTNAME']
    os.environ['KRB5CCNAME'] = "FILE:/tmp/krb5cc_root_ipakeytabd"

    reactor.listenTCP(port, IPAKeytabServerFactory(realm, admin_group))
    reactor.run()
