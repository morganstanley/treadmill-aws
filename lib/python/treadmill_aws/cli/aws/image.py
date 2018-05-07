"""Treadmill AWS image CLI

Create, delete and manage configurations of AWS images.
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

import logging

import click

from treadmill import cli
from treadmill import context
from treadmill import restclient


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
                  envvar='TREADMILL_RESTAPI')
    def image_group(api):
        """Manage Treadmill app monitor configuration"""
        ctx['api'] = api

    @image_group.command()
    @click.argument('name')
    @_ON_EXCEPTIONS
    def configure(name):
        """Configure AWS image."""
        restapi = context.GLOBAL.cell_api(ctx['api'])
        url = _REST_PATH + name
        image_entry = restclient.get(restapi, url)
        cli.out(formatter(image_entry.json()))

    @image_group.command(name='list')
    @_ON_EXCEPTIONS
    def _list():
        """List AWS images."""
        restapi = context.GLOBAL.cell_api(ctx['api'])
        url = _REST_PATH
        response = restclient.get(restapi, url)
        cli.out(formatter(response.json()))

    @image_group.command()
    @click.argument('name', nargs=1, required=True)
    @_ON_EXCEPTIONS
    def delete(name):
        """Delete AWS image"""
        restapi = context.GLOBAL.cell_api(ctx['api'])
        url = _REST_PATH + name
        restclient.delete(restapi, url)

    del delete
    del _list
    del configure

    return image_group
