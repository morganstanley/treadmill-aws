"""Tools to configure Treadmill cell."""


from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time

import click
import jinja2
import six

from treadmill import admin
from treadmill import cli
from treadmill import context
from treadmill import yamlwrapper as yaml
from treadmill.api import instance
from treadmill.scheduler import masterapi
from treadmill import sysinfo
from treadmill.syscall import krb5

from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli


_LOGGER = logging.getLogger(__name__)


# TODO: full list of cell apps:
#       adminapi, wsapi, app-dns, stateapi, cellapi
_CELL_APPS = [
    'adminapi',
    'app-dns',
    'appmonitor',
    'cellapi',
    'cellsync',
    'scheduler',
    'stateapi',
    'trace-cleanup',
    'wsapi',
]


class CellCtx:
    """Cell context."""

    def __init__(self, cors=None, krb_realm=None):
        self.cell = context.GLOBAL.cell

        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(self.cell)

        self.proid = cell['username']
        self.data = cell.get('data')

        # Default cors origin to top level dns domain. The value is passed to
        # manifest verbatim, so need to shell escape it.
        if not cors:
            last_two = context.GLOBAL.dns_domain.split('.')[-2:]
            self.cors = '\\.'.join(last_two)
        else:
            self.cors = '\\.'.join(cors.strip('.').split('.'))

        self.krb_realm = krb_realm
        if not self.krb_realm:
            realms = krb5.get_host_realm(sysinfo.hostname())
            if realms:
                self.krb_realm = realms[0]


def _render(name, ctx):
    """Render named template."""
    jinja_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))
    template = jinja_env.get_template(name)
    return yaml.load(template.render(**ctx.__dict__))


def _render_app(appname, ctx):
    """Render manifest for given app."""
    app = _render(appname, ctx)
    fullname = '{}.{}.{}'.format(ctx.proid, appname, ctx.cell)
    return fullname, app


def _monitors(ctx):
    """Load monitor definitions."""
    return _render('monitors', ctx)


def _appgroups(ctx):
    """Load appgroups definitions."""
    return _render('appgroups', ctx)


def _ident_groups(ctx):
    """Load identity group definitions."""
    return _render('identity-groups', ctx)
