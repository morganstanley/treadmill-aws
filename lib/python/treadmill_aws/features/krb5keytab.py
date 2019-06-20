"""Configures krb5keytab inside the container."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals


import logging
import os

from treadmill.appcfg.features import feature_base
from treadmill import appcfg
from treadmill import subproc
from treadmill import sysinfo

_LOGGER = logging.getLogger(__name__)


class Krb5KeytabFeature(feature_base.Feature):
    """webauthd manifest feature."""

    def applies(self, manifest, runtime):
        return runtime == 'linux'

    def configure(self, manifest):
        _LOGGER.info('Configuring krb5keytab.')

        unique_name = appcfg.manifest_unique_name(manifest)
        appdir = os.path.join(
            self._tm_env.apps_dir, unique_name, 'data', 'root'
        )

        krb5keytab_svc = {
            'name': 'krb5keytab',
            'restart': {
                'limit': 5,
                'interval': 60,
            },
            'proid': 'root',
            'root': True,
            'command': (
                '{treadmill}/bin/treadmill --debug admin krb5keytab'
                ' --owner {user}'
                ' --principal {user}/{hostname}'
                ' --keytab {appdir}/var/spool/keytabs/{user}'
                ' --cachedir /tmp'
                ' --lockdir /tmp'
                '; exec sleep inf'
            ).format(
                treadmill=subproc.resolve('treadmill'),
                user=manifest['proid'],
                hostname=sysinfo.hostname(),
                appdir=appdir,
            ),
            'environ': [{
                'name': 'KRB5CCNAME',
                'value': os.path.expandvars('FILE:${TREADMILL_HOST_TICKET}'),
            }],
            'config': None,
            'downed': False,
            'trace': False,
            'logger': 's6.logger.run',
        }
        manifest['system_services'].append(krb5keytab_svc)
