"""Treadmill AWS image API.
"""

from treadmill import authz

from treadmill_aws import ec2client
from treadmill_aws import awscontext


class API(object):
    """AWS Image REST api."""

    def __init__(self):

        def _list(account=None):
            """List configured monitors."""
            ec2_conn = awscontext.GLOBAL.ec2
            if not account:
                account = awscontext.GLOBAL.sts.get_caller_identity().get(
                    'Account'
                )

            image = {}
            images = ec2client.list_images(ec2_conn, owners=[account], **image)
            return images

        def get(_rsrc_id):
            """Get AWS image configuration."""
            return {}

        def create(_rsrc_id, _rsrc):
            """Create (configure) AWS image."""
            return {}

        def update(_rsrc_id, _rsrc):
            """Update AWS image configuration."""
            return {}

        def delete(_rsrc_id):
            """Delete AWS image."""
            return None

        self.list = _list
        self.get = get
        self.create = create
        self.update = update
        self.delete = delete


def init(authorizer):
    """Returns module API wrapped with authorizer function."""
    api = API()
    return authz.wrap(api, authorizer)
