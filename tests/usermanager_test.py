"""Tests for aws/usermanager."""

import datetime

import unittest
from unittest import mock

import requests

from treadmill import exc

import treadmill_aws
from treadmill_aws import usermanager
from treadmill_aws import ipaclient


# pylint: disable=protected-access
class UsermanagerTest(unittest.TestCase):
    """Tests usermanager interface"""

    @mock.patch('treadmill_aws.ipaclient.get_ipa_server_from_dns',
                mock.MagicMock())
    def setUp(self):
        treadmill_aws.ipaclient.get_ipa_server_from_dns.return_value = \
            'ipa-server.mydomain.x'
        self.ipaclient = ipaclient.IPAClient('certs', 'domain')

    class FakeResponse(object):
        """Fake IPA response object.
        """
        text = 'foo'
        status_code = 200

        def json(self=None):
            """Fake JSON response.
            """
            return {'error': None,
                    'result': {'result': {'foo': 'bar'}}}

    @mock.patch('subprocess.check_call',
                return_value=mock.MagicMock())
    @mock.patch('requests.post',
                return_value=mock.MagicMock(requests.Response))
    def test_create_ipa_user(self, resp_mock, subproc_mock):
        """Test create_ipa_user.
        """
        resp_mock.return_value = self.FakeResponse

        result = usermanager.create_ipa_user(
            ipa_client=self.ipaclient,
            kadmin='admin',
            ktadmin='/tmp/admin.keytab',
            user_name='foo',
            first_name='fname',
            last_name='lname',
            user_type='proid'
        )

        subproc_mock.assert_called_with(
            ['kadmin', '-p', 'admin',
             '-k', '-t', '/tmp/admin.keytab', 'cpw', '-randkey', 'foo']
        )

    @mock.patch('subprocess.check_call',
                return_value=mock.MagicMock())
    @mock.patch('requests.post',
                return_value=mock.MagicMock(requests.Response))
    def test_create_ipa_user_no_creds(self, resp_mock, subproc_mock):
        """Test create_ipa_user with invalid creds.
        """
        resp_mock.return_value = self.FakeResponse
        resp_mock.return_value.text = \
            'Unable to verify your Kerberos credentials'

        self.assertRaises(
            ipaclient.AuthenticationError,
            usermanager.create_ipa_user,
            ipa_client=self.ipaclient,
            kadmin='admin',
            ktadmin='/tmp/admin.keytab',
            user_name='foo',
            first_name='fname',
            last_name='lname',
            user_type='proid'
        )

        self.assertFalse(subproc_mock.called)

    @mock.patch('subprocess.check_call',
                return_value=mock.MagicMock())
    @mock.patch('requests.post',
                return_value=mock.MagicMock(requests.Response))
    def test_create_ipa_user_exists(self, resp_mock, subproc_mock):
        """Test create_ipa_user when user already exists.
        """
        # IPA always return 200
        resp_mock.return_value.status_code = 200
        json_mock = mock.MagicMock()
        json_mock.return_value = {
            'error': {
                'code': 4002,
                'message': 'error',
            },
        }
        resp_mock.return_value.json = json_mock

        self.assertRaises(
            ipaclient.AlreadyExistsError,
            usermanager.create_ipa_user,
            ipa_client=self.ipaclient,
            kadmin='admin',
            ktadmin='/tmp/admin.keytab',
            user_name='foo',
            first_name='fname',
            last_name='lname',
            user_type='proid'
        )

        self.assertFalse(subproc_mock.called)

    @mock.patch('treadmill_aws.iamclient.get_user', mock.Mock())
    def test_create_iam_user(self):
        """Test create_iam_user
        """
        treadmill_aws.iamclient.get_user.side_effect = exc.NotFoundError('x')

        iam_conn = mock.MagicMock()
        iam_conn.create_user.return_value = {'User': {
            'Arn': 'arn:aws:iam::236968667438:user/r',
            'CreateDate': datetime.datetime(2018, 5, 15, 19, 10, 52, 915000),
            'Path': '/',
            'UserId': 'ABCDFEFGABCDEFG',
            'UserName': 'r'
        }}

        result = usermanager.create_iam_user(
            iam_conn,
            user_name='foo'
        )

        iam_conn.create_user.assert_called_with(UserName='foo', Path='/')

    @mock.patch('treadmill_aws.iamclient.get_role', mock.Mock())
    def test_create_iam_role(self):
        """Test create_iam_user
        """
        treadmill_aws.iamclient.get_role.side_effect = exc.NotFoundError('x')

        iam_conn = mock.MagicMock()
        iam_conn.create_role.return_value = {'Role': {
            'Arn': 'arn:aws:iam::236968667438:role/xxx',
            'Path': '/',
            'RoleId': 'ABSDEFGABCDEFG',
            'RoleName': 'xxx',
            'AssumeRolePolicyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {'Action': 'sts:AssumeRole',
                     'Effect': 'Allow',
                     'Principal': {'AWS': 'arn:aws:iam::12345:root'}}
                ]
            }
        }}

        result = usermanager.create_iam_role(
            iam_conn,
            role_name='xxx',
            policy={'foo': 'bar'},
        )

        iam_conn.create_role.assert_called_with(
            RoleName='xxx',
            Path='/',
            AssumeRolePolicyDocument='{"foo": "bar"}'
        )
