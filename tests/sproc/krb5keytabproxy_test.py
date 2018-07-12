"""Test for krb5keytabproxy."""

import base64
import json
import unittest

import mock

import treadmill
from treadmill_aws.sproc import krb5keytabproxy


# pylint: disable=protected-access

class Krb5keytabProxyTest(unittest.TestCase):
    """Tests krb5keytab proxy."""

    @mock.patch('treadmill.gssapiprotocol.GSSAPILineClient.connect',
                mock.Mock(return_value=mock.MagicMock()))
    @mock.patch('treadmill.gssapiprotocol.GSSAPILineClient.disconnect',
                mock.Mock(return_value=mock.MagicMock()))
    @mock.patch('treadmill.gssapiprotocol.GSSAPILineClient.write',
                mock.Mock(return_value=mock.MagicMock()))
    @mock.patch('treadmill.gssapiprotocol.GSSAPILineClient.read',
                mock.Mock(return_value=json.dumps({
                    'status': 'success',
                    'result': {
                        'keytab_entries': base64.encodebytes(b'abc').decode()
                    }
                }).encode('utf8')))
    @mock.patch('treadmill.fs.write_safe', mock.Mock())
    def test_request_keytab(self):
        """Tests client request."""
        proxy = krb5keytabproxy.Krb5KeytabProxy(
            'my-hostname.my-domain',
            'my-ipa.domain',
            ['kt-srv1:1234', 'kt-srv2:1234'],
            '/key/tab/dir'
        )
        proxy.uid = 1
        proxy.gid = 2
        proxy.username = 'xxx'
        proxy.transport = mock.MagicMock()

        encoded = json.dumps({'keytab': True}).encode('utf8')
        proxy.got_line(encoded)
        treadmill.gssapiprotocol.GSSAPILineClient.write.assert_called_with(
            b'xxx/my-hostname.my-domain'
        )
        treadmill.fs.write_safe.assert_called_with(
            '/key/tab/dir/xxx',
            mock.ANY,
            owner=(1, 2)
        )
        treadmill.fs.write_safe.reset_mock()
        encoded = json.dumps({}).encode('utf8')
        proxy.got_line(encoded)
        treadmill.gssapiprotocol.GSSAPILineClient.write.assert_called_with(
            b'xxx/my-hostname.my-domain'
        )
        self.assertFalse(treadmill.fs.write_safe.called)

    @mock.patch('treadmill.fs.write_safe', mock.Mock())
    def test_write_keytab(self):
        """Tests writing keytab."""
        proxy = krb5keytabproxy.Krb5KeytabProxy(
            'my-hostname.my-domain',
            'my-ipa.domain',
            ['kt-srv1:1234', 'kt-srv2:1234'],
            '/key/tab/dir'
        )
        proxy.uid = 1
        proxy.gid = 2
        proxy.username = 'xxx'

        proxy._write_keytab({
            'result': {
                'keytab_entries': base64.encodebytes(b'abc')
            },
        })

        treadmill.fs.write_safe.assert_called_with(
            '/key/tab/dir/xxx',
            mock.ANY,
            owner=(1, 2)
        )
