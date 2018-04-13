"""Treadmill Host REST API."""
from treadmill import authz
from treadmill_aws.aws.manager import HostManager


class API(object):
    """Treadmill Host REST API."""

    def __init__(self):
        host_manager = HostManager()

        def create_hosts(ami,
                         cert,
                         count,
                         domain,
                         key,
                         proxy,
                         role,
                         secgroup,
                         size,
                         subnet):
            """ Create host """
            host_manager.create_host(image_id=ami,
                                     cert=cert,
                                     count=count,
                                     domain=domain,
                                     key=key,
                                     proxy=proxy,
                                     role=role,
                                     secgroup_ids=secgroup,
                                     instance_type=size,
                                     subnet_id=subnet)

        def delete_hosts(cert, hostnames):
            """ Delete host """
            host_manager.delete_hosts(cert=cert, hostnames=hostnames)

        def list_hosts(cert, hostnames=""):
            """ List host """
            return host_manager.find_hosts(cert=cert, pattern=hostnames)

        self.create = create_hosts
        self.delete = delete_hosts
        self.list = list_hosts


def init(authorizer):
    """Returns module API wrapped with authorizer function."""
    api = API()
    return authz.wrap(api, authorizer)
