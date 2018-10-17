"""Configure treadmill environment variables for sysctl.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

import click
import requests
from six.moves import http_client
import yaml

from treadmill_aws import noproxy


_USERDATA_URL = 'http://169.254.169.254/latest/user-data'


def _load_userdata(url):
    """Reads user data as dictionary."""
    with noproxy.NoProxy() as _proxy:
        resp = requests.get(url)

    if resp.status_code == http_client.NOT_FOUND:
        return {}

    return yaml.load(resp.text)


def _write_env_file(conf_file, userdata, prefixes=()):
    """Read userdata and print environment variables for each."""
    for key, value in userdata.items():
        for prefix in prefixes:
            if key.startswith(prefix) and value:
                conf_file.write('{}={}\n'.format(key.upper(), value))


def _exec(userdata, args, prefixes=()):
    """Set environment from user data and exec."""
    for key, value in userdata.items():
        for prefix in prefixes:
            if key.startswith(prefix) and value:
                os.environ[key.upper()] = value
    os.execvp(args[0], args)


@click.group()
@click.option('--userdata', help='Userdata url',
              default=_USERDATA_URL)
@click.pass_context
def syscfg(ctx, userdata):
    """Configures environment for Treadmill systemd services."""
    ctx.obj['USERDATA_URL'] = userdata


@syscfg.command()
@click.option('--envfile',
              required=True,
              type=click.File(mode='w'),
              help='Environent file location.')
@click.option('--prefix',
              multiple=True,
              default=['treadmill_'],
              help='Environent variable location.')
@click.pass_context
def write(ctx, envfile, prefix):
    """Configure environment vars."""
    url = ctx.obj['USERDATA_URL']
    userdata = _load_userdata(url)
    _write_env_file(envfile, userdata, prefix)


@syscfg.command(name='exec')
@click.option('--prefix',
              multiple=True,
              default=['treadmill_'],
              help='Environent variable location.')
@click.argument('command', nargs=-1)
@click.pass_context
def exec_cmd(ctx, prefix, command):
    """Read environment from userdata and exec."""
    url = ctx.obj['USERDATA_URL']
    userdata = _load_userdata(url)
    _exec(userdata, list(command), prefix)


def run():
    """Console entry point."""
    # Pylint complains about click signature magic.
    #
    # [E1123(unexpected-keyword-arg), run] \
    #     Unexpected keyword argument 'obj' in function call
    #
    # [E1120(no-value-for-parameter), run] \
    #     No value for argument 'ctx', 'userdata' in function call
    #
    # pylint: disable=E1120,E1123
    syscfg(obj={})
