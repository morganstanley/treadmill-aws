"""Treadmill Zookeeper Plugin.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

import kazoo.client
import kazoo.security

from treadmill import zkutils

_ROLES = {
    'admin': 'admins',
}

_DEFAULT_ZK_SERVICE = 'zookeeper'

_LOGGER = logging.getLogger('__name__')


class SASLZkClient(zkutils.ZkClient):
    """ZkClient implementation using SASL base authentication.
    """

    def __init__(self, **connargs):
        """Foo
        """
        if 'hosts' in connargs and '@' in connargs['hosts']:
            zkservice, _, zkhosts = connargs['hosts'].partition('@')
            connargs['hosts'] = zkhosts
        else:
            zkservice = _DEFAULT_ZK_SERVICE

        if 'sasl_data' not in connargs:
            connargs['sasl_data'] = {
                'service': zkservice,
                'mechanisms': ['GSSAPI']
            }
        else:
            connargs['sasl_data']['service'] = zkservice

        _LOGGER.debug('SASL Kerberos connection to Zookeeper: %r', connargs)
        super().__init__(**connargs)

    def make_user_acl(self, user, perm):
        """Create user acl in zookeeper.

        ACL properties:
            - schema: sasl
            - credential: <user>
        """
        return kazoo.security.make_acl(
            scheme='sasl', credential=user,
            read='r' in perm,
            write='w' in perm,
            create='c' in perm,
            delete='d' in perm,
            admin='a' in perm
        )

    def make_role_acl(self, role, perm):
        """Create role acl in zookeeper.

        Roles are sourced from our LDAP lookup plugin, in the format
        'role/<role>.
        """
        credential = 'role/{0}'.format(_ROLES.get(role, role))
        return kazoo.security.make_acl(
            scheme='sasl',
            credential=credential,
            read='r' in perm,
            write='w' in perm,
            create='c' in perm,
            delete='d' in perm,
            admin='a' in perm
        )

    def make_host_acl(self, host, perm):
        """Create host acl in zookeeper.
        """
        return kazoo.security.make_acl(
            scheme='sasl', credential='host/{0}'.format(host),
            read='r' in perm,
            write='w' in perm,
            create='c' in perm,
            delete='d' in perm,
            admin='a' in perm
        )


__all__ = (
    'SASLZkClient',
)
