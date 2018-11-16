"""Tests for ipa525 server."""

import pwd

import unittest
from unittest import mock

import treadmill
from treadmill import authz

from treadmill_aws import ipa525


# pylint: disable=protected-access
class IPA525Test(unittest.TestCase):
    """Tests ipa525 server."""

    @mock.patch('pwd.getpwnam', mock.Mock())
    def test_validate(self):
        """Test request validation.
        """
        ipasrv = ipa525.IPA525Server(
            client_realm=['c_realm.org'],
            server_realm='s_realm.org',
            authz_remote=None
        )

        pwd.getpwnam.return_value = 123
        ipasrv._validate('foo@s_realm.org')

        # Invalid request - instance.
        self.assertRaises(
            ValueError, ipasrv._validate, 'foo/hostname@s_realm.org'
        )

        # Invalid realm.
        self.assertRaises(
            ValueError, ipasrv._validate, 'foo@invalid.org'
        )

        # Invalid user:
        pwd.getpwnam.side_effect = ValueError
        self.assertRaises(
            ValueError, ipasrv._validate, 'foo@s_realm.org'
        )

    @mock.patch('treadmill.restclient.post', mock.Mock())
    def test_authorize(self):
        """Test request authorization."""

        ipasrv = ipa525.IPA525Server(
            client_realm=['c_realm.org'],
            server_realm='s_realm.org',
            authz_remote=None
        )

        # Successful self authorization.
        ipasrv._authorize('user1@c_realm.org', 'user1@s_realm.org')

        # Invalid client realm.
        self.assertRaises(
            authz.AuthorizationError,
            ipasrv._authorize, 'user1@someother.org', 'user1@s_realm.org'
        )

        # Different user, authorized is not specified.
        self.assertRaises(
            authz.AuthorizationError,
            ipasrv._authorize, 'user1@c_realm.org', 'user2@s_realm.org'
        )

        ipasrv.authorizer = authz.ClientAuthorizer(
            lambda: 'userX@c_realm.org',
            '/var/run/auth.sock'
        )

        # Successful self authorization.
        ipasrv._authorize('user1@c_realm.org', 'user1@s_realm.org')
        self.assertFalse(treadmill.restclient.post.called)

        # Impersonation request
        treadmill.restclient.post.return_value = mock.MagicMock()
        ipasrv._authorize('userX@c_realm.org', 'user2@s_realm.org')
        treadmill.restclient.post.assert_called_with(
            ['/var/run/auth.sock'],
            '/userX@c_realm.org/ipa525/user',
            payload={'payload': None, 'pk': 'user2'}
        )

    @mock.patch('treadmill.restclient.post', mock.Mock())
    @mock.patch('treadmill_aws.ipa525.IPA525Server._validate', mock.Mock())
    @mock.patch('treadmill_aws.ipa525.IPA525Server._authorize', mock.Mock())
    @mock.patch('treadmill_aws.ipa525.IPA525Server.peer',
                mock.Mock(return_value='user1@c_realm.org'))
    @mock.patch('treadmill_aws.ipa525.IPA525Server.peercred_lifetime',
                mock.Mock(return_value=5))
    @mock.patch('treadmill_aws.ipa525.IPA525Server._get_ticket',
                mock.Mock(return_value=b'1'))
    def test_gotline(self):
        """Test processing single request."""
        ipasrv = ipa525.IPA525Server(
            client_realm=['c_realm.org'],
            server_realm='s_realm.org',
            authz_remote=None
        )

        ipasrv.transport = mock.MagicMock()
        reply = ipasrv._process_request(b'user2@s_realm.org')
        self.assertEqual(200, reply['code'])

        ipa525.IPA525Server._validate.side_effect = ValueError
        reply = ipasrv._process_request(b'user2@s_realm.org')
        self.assertEqual(400, reply['code'])

        ipa525.IPA525Server._validate.reset()
        ipa525.IPA525Server._validate.side_effect = OSError
        reply = ipasrv._process_request(b'user2@s_realm.org')
        self.assertEqual(500, reply['code'])

        def _auth_err(*_args, **_kwargs):
            """Raise authorization error."""
            raise authz.AuthorizationError(['some error'])

        ipa525.IPA525Server._validate.side_effect = None
        ipa525.IPA525Server._authorize.side_effect = _auth_err
        reply = ipasrv._process_request(b'user2@s_realm.org')
        self.assertEqual(403, reply['code'])
