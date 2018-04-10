"""EC2 connection."""

from types import SimpleNamespace
import boto3

from treadmill_aws.infra import constants


class Singleton(type):
    """Connection is a singleton."""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        resource = kwargs.get(
            'resource',
            args[0] if args else constants.EC2
        )

        # pylint:disable=protected-access
        instance_resources = [klass._service_model.service_name.lower()
                              for klass in list(cls._instances.values())]

        if resource.lower() not in instance_resources:
            cls._instances[cls] = super(
                Singleton, cls
            ).__call__(*args, **kwargs)

        return cls._instances[cls]


class Connection(metaclass=Singleton):
    """EC2 connection instance."""

    session = boto3.session.Session()
    context = SimpleNamespace(
        region_name=session.region_name,
        domain=None
    )

    def __init__(self, resource=constants.EC2):
        pass

    def __new__(cls, resource=constants.EC2):
        return boto3.client(
            resource, region_name=cls.context.region_name
        )
