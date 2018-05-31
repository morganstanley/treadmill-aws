"""AWS specific aliases.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

_LINUX_ALIASES = {
    # Automounter
    'amq': None,

    # Netfilter utilities
    'conntrack': '/usr/sbin/conntrack',
    'ipset': '/usr/sbin/ipset',
    'iptables': '/sbin/iptables',
    'iptables_restore': '/sbin/iptables-restore',

    # djbdns cache.
    'dnscache': None,

    # Docker binaries.
    'docker': '/usr/bin/docker',
    'dockerd': '/usr/bin/dockerd',
    'docker_runtime': '/usr/libexec/docker/docker-runc-latest',

    # Kerberos utilities.
    'ipa': '/bin/ipa',
    'kinit': '/usr/bin/kinit',
    'klist': '/usr/bin/klist',
    'kt_add': '/usr/bin/kt_add',
    'kt_split': '/usr/bin/kt_split',

    'fio': None,
    'iozone': None,

    # Reboot command
    # TODO: need better abstraction for reboot script. It is probably ok to
    #       call it "reboot" but may need to support command line options in
    #       exe file like aliases.
    'reboot': '/usr/bin/reboot',

    # Skarnet S6
    's6': '/opt/s6',

    # Treadmill PID1
    'pid1': '/usr/bin/pid1',

    # http://oss.oetiker.ch/rrdtool/
    'rrdcached': '/bin/rrdcached',
    'rrdtool': '/bin/rrdtool',

    # OpenLDAP distribution
    'openldap': None,
    'slapadd': '/usr/sbin/slapadd',
    'slapd': '/usr/sbin/slapd',
    'ldapsearch': None,

    # sshd
    'sshd': '/usr/sbin/sshd',

    # Treadmill utilities.
    'tkt_recv_v2': '/usr/bin/tkt-recv-v2',
    'tkt_send_v2': '/usr/bin/tkt-send-v2',

    # Shared libraries.
    #
    # ld_preload libs use $LIB notation, and in the code should be resolved
    # with check=False.
    #
    'treadmill_bind_distro': '/opt/treadmill-bind',
    'treadmill_bind_preload.so': (
        '/opt/treadmill-bind/$LIB/libtreadmill_bind_preload.so'
    ),

    # Linux Volume Manager
    'lvm': '/sbin/lvm',
    'pvremove': '/sbin/pvremove',
    'pvs': '/sbin/pvs',
    'vgchange': '/sbin/vgchange',
    'vgremove': '/sbin/vgremove',
}

_WINDOWS_ALIASES = {
}


if os.name == 'nt':
    ALIASES = _WINDOWS_ALIASES
else:
    ALIASES = _LINUX_ALIASES
