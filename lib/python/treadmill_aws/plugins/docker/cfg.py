"""Manage AWS docker configure.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import socket

from treadmill import nodedata
from treadmill import dockerutils

_LOGGER = logging.getLogger(__name__)


def get_tls_config(tm_env):
    """Return the paths to the TLS certificate on the host
    :returns:
        ``dict(ca_cert=str, host_cert=str, host_key=str, tls_verify=bool,...)``
        -- path to ca root cert, host cert, host key, tls enabled
    """
    # get tls parameters from node.json
    data = nodedata.get(tm_env.configs_dir)

    (tls_verify,
     ca_cert,
     host_cert,
     host_keys) = dockerutils.get_tls_config(data)

    # compatible with old logic
    if ca_cert:
        tls_verify = True

    return {
        'tls_verify': tls_verify,
        'ca_cert': ca_cert,
        'host_cert': host_cert,
        'host_key': host_key,
    }


def get_docker_registry(tm_env, app_environment):
    """Return the registry values
    """
    # get registries address from node.json
    data = nodedata.get(tm_env.configs_dir)

    registries = dockerutils.get_registries(app_environment, data)
    (tls_verify,
     ca_cert,
     _host_cert,
     _host_keys) = dockerutils.get_tls_config(data)

    # in old logic, if ca_cert has value, it means tls is enabled
    # Then we disable insecure registry
    insecure = False if (ca_cert or tls_verify) else True

    normalized_reg = []
    for registry in registries:
        if ':' in registry:
            host, _sep, port = registry.partition(':')
        else:
            host = registry
            port = None

        # XXX: Ensure we have FQDN for registry hosts.
        host = socket.getfqdn(host)
        res = [host, port] if port is not None else [host]
        normalized_reg.append(':'.join(res))

    return (normalized_reg, insecure)
