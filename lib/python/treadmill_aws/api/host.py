"""Treadmill Host REST API."""
from treadmill import authz

from treadmill_aws import hostmanager
from treadmill_aws import awscontext


class API:
    """Treadmill Host REST API."""

    def __init__(self):

        def create_hosts(ami,
                         count,
                         disk,
                         domain,
                         key,
                         role,
                         secgroup,
                         size,
                         subnet):
            """Create host."""

            ipa_client = awscontext.GLOBAL.ipaclient
            ec2_conn = awscontext.GLOBAL.ec2

            hostmanager.create_host(
                ipa_client=ipa_client,
                ec2_conn=ec2_conn,
                image_id=ami,
                count=count,
                domain=domain,
                key=key,
                role=role,
                secgroup_ids=secgroup,
                instance_type=size,
                subnet_id=subnet,
                disk=disk,
                instance_vars=None)

        def delete_hosts(hostnames):
            """Delete host."""
            ipa_client = awscontext.GLOBAL.ipaclient
            ec2_conn = awscontext.GLOBAL.ec2

            hostmanager.delete_hosts(
                ipa_client=ipa_client,
                ec2_conn=ec2_conn,
                hostnames=hostnames
            )

        def list_hosts(hostnames=None):
            """List hostr."""
            ipa_client = awscontext.GLOBAL.ipaclient

            return hostmanager.find_hosts(
                ipa_client=ipa_client,
                pattern=hostnames
            )

        self.create = create_hosts
        self.delete = delete_hosts
        self.list = list_hosts


def init(authorizer):
    """Returns module API wrapped with authorizer function."""
    api = API()
    return authz.wrap(api, authorizer)
