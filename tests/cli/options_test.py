"""Test for click AWS options parsing."""

import unittest

import click
from click.testing import CliRunner

from treadmill_aws.cli import options


class ImageOptionsTest(unittest.TestCase):
    """Tests EC2 client interface"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_id_opt(self):
        """Test image options construction."""

        args = dict()

        @click.command()
        @options.make_image_opts(args)
        def image():
            """Test cli."""
            pass

        runner = CliRunner()
        result = runner.invoke(image, ['--image-id', 'ami-1234'])

        self.assertEqual(result.output, '')
        self.assertEqual(args['id'], 'ami-1234')
        self.assertFalse(args['tags'])

    def test_name_owner(self):
        """Test image options construction."""

        args = dict()

        @click.command()
        @options.make_image_opts(args)
        def image():
            """Test cli."""
            pass

        runner = CliRunner()
        result = runner.invoke(
            image, ['--image-name', 'xxx', '--image-owner', 'yyy']
        )

        self.assertEqual(result.output, '')
        self.assertIsNone(args.get('id'))
        self.assertEqual(args['name'], 'xxx')
        self.assertEqual(args['owner'], 'yyy')
        self.assertFalse(args['tags'])


class SubnetOptionsTest(unittest.TestCase):
    """Tests EC2 client interface"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_id_opt(self):
        """Test image options construction."""

        args = dict()

        @click.command()
        @options.make_subnet_opts(args)
        def subnet():
            """Test cli."""
            pass

        runner = CliRunner()
        result = runner.invoke(subnet, ['--subnet-id', 'subnet-1234'])

        self.assertEqual(result.output, '')
        self.assertEqual(args['id'], 'subnet-1234')
        self.assertFalse(args['tags'])

    def test_tags(self):
        """Test image options construction."""

        args = dict()

        @click.command()
        @options.make_subnet_opts(args)
        def subnet():
            """Test cli."""
            pass

        runner = CliRunner()
        result = runner.invoke(
            subnet, ['--subnet-name', 'xxx']
        )

        self.assertEqual(result.output, '')
        self.assertIsNone(args.get('id'))
        self.assertEqual(args['tags'], {'Name': ['xxx']})


class SecgroupOptionsTest(unittest.TestCase):
    """Tests EC2 client interface"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_id_opt(self):
        """Test image options construction."""

        args = dict()

        @click.command()
        @options.make_secgroup_opts(args)
        def secgroup():
            """Test cli."""
            pass

        runner = CliRunner()
        result = runner.invoke(secgroup, ['--secgroup-id', 'secgroup-1234'])

        self.assertEqual(result.output, '')
        self.assertEqual(args['id'], 'secgroup-1234')
        self.assertFalse(args['tags'])

    def test_tags(self):
        """Test image options construction."""

        args = dict()

        @click.command()
        @options.make_secgroup_opts(args)
        def secgroup():
            """Test cli."""
            pass

        runner = CliRunner()
        result = runner.invoke(
            secgroup, ['--secgroup-name', 'xxx']
        )

        self.assertEqual(result.output, '')
        self.assertIsNone(args.get('id'))
        self.assertEqual(args['tags'], {'Name': ['xxx']})
