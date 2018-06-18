"""Admin Cell CLI module
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time

import click
import jinja2
from ldap3.core import exceptions as ldap_exceptions
import six

from treadmill import admin
from treadmill import cli
from treadmill import context
from treadmill import yamlwrapper as yaml
from treadmill.api import instance
from treadmill.scheduler import masterapi


_LOGGER = logging.getLogger(__name__)


# TODO: full list of cell apps:
#       adminapi, wsapi, app-dns, stateapi, cellapi
_CELL_APPS = [
    'scheduler', 'appmonitor', 'wsapi', 'stateapi', 'cellapi', 'cellsync',
    'trace-cleanup',
]


class CellCtx(object):
    """Cell context."""

    def __init__(self, cors=None, krb_realm=None):
        self.cell = context.GLOBAL.cell

        admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
        cell = admin_cell.get(self.cell)

        self.proid = cell['username']
        self.data = cell.get('data')
        self.location = cell['location']

        # Default cors origin to top level dns domain. The value is passed to
        # manifest verbatim, so need to shell escape it.
        if not cors:
            last_two = context.GLOBAL.dns_domain.split('.')[-2:]
            self.cors = '\\.'.join(last_two)
        else:
            self.cors = '\\.'.join(cors.strip('.').split('.'))

        self.krb_realm = krb_realm
        if not self.krb_realm:
            self.krb_realm = context.GLOBAL.dns_domain.upper()


def _render(name, ctx):
    """Render named template."""
    jinja_env = jinja2.Environment(loader=jinja2.PackageLoader(__name__))
    template = jinja_env.get_template(name)
    return yaml.load(template.render(**ctx.obj.__dict__))


def _render_app(appname, ctx):
    """Render manifest for given app."""
    app = _render(appname, ctx)
    fullname = '{}.{}.{}'.format(ctx.obj.proid, appname, ctx.obj.cell)
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


def init():
    """Admin Cell CLI module"""

    @click.group(name='cell')
    @click.option('--cors-origin', help='CORS origin for API.')
    @click.option('--cell', required=True,
                  envvar='TREADMILL_CELL',
                  is_eager=True, callback=cli.handle_context_opt,
                  expose_value=False)
    @click.option('--krb-realm', help='Kerberos realm',
                  envvar='TREADMILL_KRB_REALM',
                  required=False)
    @click.pass_context
    def cell_grp(ctx, cors_origin, krb_realm):
        """Manage treadmill cell."""
        ctx.obj = CellCtx(cors=cors_origin, krb_realm=krb_realm)

    @cell_grp.command(name='configure-apps')
    @click.option('--apps', type=cli.LIST, help='List of apps to configure.')
    @click.pass_context
    def configure_apps(ctx, apps):
        """Configure cell API."""
        admin_app = admin.Application(context.GLOBAL.ldap.conn)

        # For apps that need write access to LDAP. The context LDAP must have
        # write access because this is what we use to write manifests here.
        write_uri = admin_app.admin.write_uri
        ctx.obj.admin_ldap_url = ','.join(write_uri) if write_uri else None

        if not apps:
            apps = _CELL_APPS

        # Configure apps identity groups
        identity_groups = _ident_groups(ctx)
        for groupname, count in six.iteritems(identity_groups):
            masterapi.update_identity_group(
                context.GLOBAL.zk.conn,
                groupname,
                count
            )

        # Configure apps
        for appname in apps:
            fullname, app = _render_app(appname, ctx)
            print(fullname)
            print(yaml.dump(app))
            try:
                admin_app.create(fullname, app)
            except ldap_exceptions.LDAPEntryAlreadyExistsResult:
                admin_app.replace(fullname, app)

    @cell_grp.command(name='configure-monitors')
    @click.option('--monitors', type=cli.DICT,
                  help='Key/value pairs for monitor count overrides.')
    @click.pass_context
    def configure_monitors(ctx, monitors):
        """Configure system apps monitors."""
        if not monitors:
            monitors = _monitors(ctx)

        for name, count in six.iteritems(monitors):
            print(name, count)
            masterapi.update_appmonitor(
                context.GLOBAL.zk.conn,
                name,
                int(count)
            )

    @cell_grp.command(name='restart-apps')
    @click.option('--apps', type=cli.LIST,
                  help='List of apps to restart.')
    @click.option('--wait', type=int, help='Interval to wait before re-start.',
                  default=20)
    @click.pass_context
    def restart_apps(ctx, wait, apps):
        """Restart cell API."""
        instance_api = instance.API(plugins=['aws-proid-env'])
        monitors = _monitors(ctx)
        for name, count in six.iteritems(monitors):
            _, appname, _ = name.split('.')
            if apps and appname not in apps:
                continue

            _, app = _render_app(appname, ctx)
            print(name)
            print(yaml.dump(app))
            for idx in range(0, count):
                instance_ids = instance_api.create(name, app, 1)
                for inst_id in instance_ids:
                    print(inst_id)
                if idx <= count - 1 and wait:
                    time.sleep(wait)

    @cell_grp.command(name='configure-appgroups')
    @click.pass_context
    def configure_appgroups(ctx):
        """Configure system app groups."""
        appgroups = _appgroups(ctx)

        admin_app_group = admin.AppGroup(context.GLOBAL.ldap.conn)
        for name, data in six.iteritems(appgroups):
            print(name, data)
            try:
                admin_app_group.create(name, data)
            except ldap_exceptions.LDAPEntryAlreadyExistsResult:
                admin_app_group.update(name, data)

            existing = admin_app_group.get(name, dirty=True)
            group_cells = set(existing['cells'])
            group_cells.update([ctx.obj.cell])
            admin_app_group.update(name, {'cells': list(group_cells)})
            existing = admin_app_group.get(name, dirty=True)
            print(existing)

    del restart_apps
    del configure_apps
    del configure_monitors
    del configure_appgroups

    return cell_grp
