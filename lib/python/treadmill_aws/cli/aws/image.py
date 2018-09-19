"""Treadmill AWS image CLI

Create, delete and manage configurations of AWS images.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

import gzip
import io
import logging

import click

from treadmill import cli
from treadmill import restclient

from treadmill_aws import cli as aws_cli


_LOGGER = logging.getLogger(__name__)

_EXCEPTIONS = []
_EXCEPTIONS.extend(restclient.CLI_REST_EXCEPTIONS)

_ON_EXCEPTIONS = cli.handle_exceptions(_EXCEPTIONS)

_REST_PATH = '/image/'


def init():  # pylint: disable=R0912
    """Configures application monitor"""
    formatter = cli.make_formatter('aws_image')
    ctx = {}

    @click.group()
    @click.option('--api', help='API url to use.',
                  metavar='URL',
                  type=cli.LIST,
                  envvar='TREADMILL_AWSAPI')
    def image_group(api):
        """Manage Treadmill app monitor configuration"""
        ctx['api'] = api

    @image_group.command()
    @click.argument('name')
    @_ON_EXCEPTIONS
    def configure(name):
        """Configure AWS image."""
        restapi = ctx['api']
        url = _REST_PATH + name
        image_entry = restclient.get(restapi, url)
        cli.out(formatter(image_entry.json()))

    @image_group.command(name='list')
    @_ON_EXCEPTIONS
    def _list():
        """List AWS images."""
        restapi = ctx['api']
        url = _REST_PATH
        response = restclient.get(ctx['api'], url)
        cli.out(formatter(response.json()))

    @image_group.command()
    @click.argument('name', nargs=1, required=True)
    @_ON_EXCEPTIONS
    def delete(name):
        """Delete AWS image"""
        restapi = ctx['api']
        url = _REST_PATH + name
        restclient.delete(restapi, url)

    @image_group.command(name='create')
    @click.option(
        '--base-image',
        required=True,
        type=aws_cli.IMAGE,
        help='Base image.'
    )
    @click.option(
        '--base-image-account',
        required=False,
        help='Base image account.'
    )
    @click.option(
        '--userdata',
        required=True,
        type=click.Path(exists=True),
        multiple=True,
        help='Cloud-init user data.'
    )
    @click.option(
        '--instance-profile',
        required=False,
        help='Instance profile with create image privs.'
    )
    @click.option(
        '--secgroup',
        required=False,
        type=aws_cli.SECGROUP,
        help='Security group'
    )
    @click.option(
        '--subnet',
        required=False,
        type=aws_cli.SUBNET,
        help='Subnet'
    )
    @click.option(
        '--key',
        help='SSH key'
    )
    @click.argument('name', required=True, type=str)
    @_ON_EXCEPTIONS
    def create(base_image, base_image_account, userdata, instance_profile,
               secgroup, subnet, key, name):
        """Create image"""
        restapi = ctx['api']
        payload = {
            'base_image': base_image,
            'base_image_account': base_image_account,
            'instance_profile': instance_profile,
            'userdata': [],
            'secgroup': secgroup,
            'subnet': subnet,
            'key': key,
        }

        for filename in userdata:
            with io.open(filename, 'rb') as f:
                content = f.read()
                if filename.endswith('.gz'):
                    content = gzip.decompress(content)
                payload['userdata'].append(content.decode())

        url = _REST_PATH + name
        response = restclient.post(restapi, url, payload=payload)
        print(response.json())

    del delete
    del _list
    del configure
    del create

    return image_group
