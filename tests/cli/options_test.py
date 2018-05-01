"""Test for click AWS options parsing."""

import json
import unittest

import click
from click.testing import CliRunner

from treadmill_aws import cli as aws_cli


class ImageOptionsTest(unittest.TestCase):
    """Tests parsing image options"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_id_opt(self):
        """Test image options construction."""

        @click.command()
        @click.argument('args', type=aws_cli.IMAGE)
        def test(args):
            """Test cli."""
            print(json.dumps(args))

        runner = CliRunner()
        result = runner.invoke(test, ['ami-1234'])
        obj = json.loads(result.output)

        self.assertEqual(obj['ids'], ['ami-1234'])
        self.assertFalse(obj['tags'])

    def test_image_name(self):
        """Test image name options construction."""

        @click.command()
        @click.argument('args', type=aws_cli.IMAGE)
        def test(args):
            """Test cli."""
            print(json.dumps(args))

        runner = CliRunner()
        result = runner.invoke(test, ['somename'])
        obj = json.loads(result.output)

        self.assertEqual(obj['name'], 'somename')
        self.assertFalse(obj['tags'])
        self.assertNotIn('ids', obj)


class SubnetOptionsTest(unittest.TestCase):
    """Tests EC2 client interface"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_id_opt(self):
        """Test image options construction."""

        @click.command()
        @click.argument('args', type=aws_cli.SUBNET)
        def test(args):
            """Test cli."""
            print(json.dumps(args))

        runner = CliRunner()
        result = runner.invoke(test, ['subnet-1234'])
        obj = json.loads(result.output)

        self.assertEqual(obj['ids'], ['subnet-1234'])
        self.assertFalse(obj['tags'])

    def test_tags(self):
        """Test image options construction."""

        @click.command()
        @click.argument('args', type=aws_cli.SUBNET)
        def test(args):
            """Test cli."""
            print(json.dumps(args))

        runner = CliRunner()
        result = runner.invoke(test, ['Name=xxx,Version=yyy'])
        obj = json.loads(result.output)

        self.assertEqual(obj['tags']['Name'], ['xxx'])
        self.assertEqual(obj['tags']['Version'], ['yyy'])


class SecgroupOptionsTest(unittest.TestCase):
    """Tests EC2 client interface"""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_id_opt(self):
        """Test image options construction."""

        @click.command()
        @click.argument('args', type=aws_cli.SECGROUP)
        def test(args):
            """Test cli."""
            print(json.dumps(args))

        runner = CliRunner()
        result = runner.invoke(test, ['sg-1234'])
        obj = json.loads(result.output)

        self.assertEqual(obj['ids'], ['sg-1234'])
        self.assertFalse(obj['tags'])

    def test_tags(self):
        """Test image options construction."""

        @click.command()
        @click.argument('args', type=aws_cli.SECGROUP)
        def test(args):
            """Test cli."""
            print(json.dumps(args))

        runner = CliRunner()
        result = runner.invoke(test, ['Name=xxx,Version=yyy'])
        obj = json.loads(result.output)

        self.assertEqual(obj['tags']['Name'], ['xxx'])
        self.assertEqual(obj['tags']['Version'], ['yyy'])
