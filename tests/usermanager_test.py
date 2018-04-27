"""Tests for aws/usermanager."""

import unittest
from unittest import mock

from treadmill_aws import usermanager


# pylint: disable=protected-access
class UsermanagerTest(unittest.TestCase):
    """Tests usermanager interface"""

    @mock.patch('treadmill_aws.ipaclient')
    def test_create_ipa_user(self, mock_ipaclient):
        """Test create_ipa_user scenarios
        """
        # Case 1- user already exists
        mock_ipaclient.show_user = mock.MagicMock(return_value='foo')
        result = usermanager.create_ipa_user(ipa_client=mock_ipaclient,
                                             user_name='foo',
                                             first_name='fname',
                                             last_name='lname',
                                             user_type='proid')
        assert result == 'foo'

        # Case 2- user does not yet exist
        mock_ipaclient.show_user = mock.MagicMock(side_effect=KeyError('foo'))
        usermanager.create_ipa_user(ipa_client=mock_ipaclient,
                                    user_name='foo',
                                    first_name='fname',
                                    last_name='lname',
                                    user_type='proid')
        # assert mock_ipaclient.add_user.assert_called_with(user_type='proid',
        #                                                   first_name='fname',
        #                                                   user_name='foo',
        #                                                   last_name='lname')

    def test_create_iam_user(self):
        """Test create_iam_user
           Case 1- user already exists
           Case 2- user does not yet exist
        """
        pass

    def test_create_user(self):
        """Test create_user
           Case 1- Test output formatting
        """
        pass

    def test_delete_user(self):
        """Test delete_iam_user
           Case 1- user has already been deleted
           Case 2- user has not yet been deleted
        """
        pass

    def test_list_users(self):
        """Test list_users
           Case 1- no search pattern
           Case 2- search pattern 'proid'
        """
        pass
