"""Treadmill AWS openldap bootstrap.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from .. import aws_aliases as aliases


DEFAULTS = {
    'dir_config': '{{ dir }}/etc/openldap',
    'dir_schema': '{{ dir_config }}/schema',
    'attribute_options': ['tm-'],
    'backends': [
        {
            'name': '{0}config',
            'ldap_admins': '{{ ldap_admins }}',
            'rootdn': 'cn=Manager,cn=config',
            'rootpw': '{{ rootpw }}',
            'suffix': 'cn=config',
            'syncrepl_searchbase': 'cn={1}treadmill,cn=schema,cn=config'
        },
        {
            'name': '{1}mdb',
            'objectclass': 'olcMdbConfig',
            'ldap_admins': '{{ ldap_admins }}',
            'rootdn': 'cn=Manager,{{ suffix }}',
            'rootpw': '{{ rootpw }}',
            'suffix': '{{ suffix }}',
            'syncrepl_searchbase': '{{ suffix }}',
            'index': {
                'objectClass': 'eq',
                'entryCSN': 'eq',
            },
        }
    ],
    'log_levels': [16384],
    'schemas': ['file:///etc/openldap/schema/core.ldif']
}


ALIASES = aliases.ALIASES
