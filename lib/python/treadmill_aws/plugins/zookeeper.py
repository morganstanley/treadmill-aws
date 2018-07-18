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
from treadmill import utils
from treadmill import sysinfo
from treadmill.syscall import krb5

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

    def make_self_acl(self, perm):
        """Constucts acl for the current user.

        If the user is root, use host principal.
        """
        if utils.is_root():
            return self.make_host_acl(sysinfo.hostname(), perm)

        user = krb5.get_principal()
        return self.make_user_acl(user, perm)

    def make_role_acl(self, role, perm):
        """Create role acl in zookeeper.

        Roles are sourced from our LDAP lookup plugin, in the format
        'role/<role>.
        """
        # TODO: enable role ACLs when role authorizer is implemented. Until
        #       then, allow any authenticated user.
        #
        # credential = 'role/{0}'.format(_ROLES.get(role, role))
        # return kazoo.security.make_acl(
        #     scheme='sasl',
        #     credential=credential,
        #     read='r' in perm,
        #     write='w' in perm,
        #     create='c' in perm,
        #     delete='d' in perm,
        #     admin='a' in perm
        # )

        # pylint: disable=useless-super-delegation
        return super().make_role_acl(role, perm)

    def make_host_acl(self, host, perm):
        """Create host acl in zookeeper.
        """
        realms = krb5.get_host_realm(host)
        if not realms:
            _LOGGER.critical('Host %s does not belong to krb realm.', host)
            raise Exception('Host does not belong to krb5 realm.')

        host_principal = 'host/{host}@{realm}'.format(
            host=host,
            realm=realms[0]
        )
        return kazoo.security.make_acl(
            scheme='sasl',
            credential=host_principal,
            read='r' in perm,
            write='w' in perm,
            create='c' in perm,
            delete='d' in perm,
            admin='a' in perm
        )


__all__ = (
    'SASLZkClient',
)
