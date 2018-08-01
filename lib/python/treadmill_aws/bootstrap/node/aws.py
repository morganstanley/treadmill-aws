"""Treadmill AWS node bootstrap.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from .. import aws_aliases as aliases

if os.name == 'nt':
    _DEFAULT_RUNTIME = 'docker'
else:
    _DEFAULT_RUNTIME = 'linux'

_DEFAULT_TREADMILL_VG = 'treadmill'
_DEFAULT_HOST_TICKET = '{{ dir }}/spool/tickets/krb5cc_host'

DEFAULTS = {
    'treadmill_runtime': _DEFAULT_RUNTIME,
    'treadmill_host_ticket': _DEFAULT_HOST_TICKET,
    'system_cpuset_cores': '0',
    'treadmill_apps_cpuset_cpus': '1-',
    'treadmill_core_cpuset_cpus': '0',
    'treadmill_core_cpu_shares': '1%',
    'treadmill_core_mem': '-1',
    'treadmill_cpu_shares': '90%',
    'treadmill_mem': '-1',
    'localdisk_img_location': '{{ dir }}',
    'localdisk_img_size': None,
    'localdisk_block_dev': None,
    'localdisk_vg_name': _DEFAULT_TREADMILL_VG,
    'block_dev_configuration': None,
    'block_dev_read_bps': None,
    'block_dev_write_bps': None,
    'block_dev_read_iops': None,
    'block_dev_write_iops': None,
    # TODO: these should be discovered based on instance type.
    'localdisk_default_read_bps': '1G',
    'localdisk_default_read_iops': 1000000,
    'localdisk_default_write_bps': '1G',
    'localdisk_default_write_iops': 1000000,
    'runtime_linux_host_mounts': (
        '/,/dev*,/proc*,/sys*,/run*,/mnt*,/etc/resolv.conf,'
    ),
    'docker_network': 'nat',
}

ALIASES = aliases.ALIASES
