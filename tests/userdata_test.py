"""Tests for aws/hostmanager."""

import unittest

from treadmill_aws import userdata


# pylint: disable=protected-access
class UserdataTest(unittest.TestCase):
    """Tests userdata interface"""

    def test_guess_content_type(self):
        """Test guessing content type from data."""
        self.assertEqual(
            'text/cloud-config',
            userdata._guess_content_type('#cloud-config\nbla')
        )
        self.assertEqual(
            'text/upstart-job',
            userdata._guess_content_type('#upstart-job\nbla')
        )
        self.assertEqual(
            'text/cloud-boothook',
            userdata._guess_content_type('#cloud-boothook\nbla')
        )
        self.assertEqual(
            'text/part-handler',
            userdata._guess_content_type('#part-handler\nbla')
        )
        self.assertEqual(
            'text/x-shellscript',
            userdata._guess_content_type('#!/bin/sh echo')
        )
        self.assertEqual(
            'text/x-include-url',
            userdata._guess_content_type('#include  \n\n http://')
        )
        self.assertIsNone(
            userdata._guess_content_type('whatever')
        )

    def test_cloud_init(self):
        """Test construction of cloud-init data."""
        cloud_init = userdata.CloudInit()
        cloud_init.add('#!/bin/sh')
        cloud_init.add('#cloud-config\na=1')
        self.assertEqual(
            cloud_init.content_by_mimetype['text/x-shellscript'],
            [('-', '#!/bin/sh')]
        )
