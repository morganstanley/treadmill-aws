"""EC2 Object."""

from treadmill_aws.infra import connection


class EC2Object:
    """EC2 object."""

    def __init__(self, name=None, instance_id=None, metadata=None, role=None):
        self._id = instance_id
        self.metadata = metadata
        self._role = role
        self._name = name
        self._ec2_conn = None

    @property
    def ec2_conn(self):
        """Lazy construction of EC2 connection."""
        if self._ec2_conn is None:
            self._ec2_conn = connection.Connection()
        return self._ec2_conn

    @ec2_conn.setter
    def ec2_conn(self, value):
        """EC2 connection, setter.
        """
        self._ec2_conn = value

    @property
    def instance_id(self):
        """Return object id."""
        return self._extract_id() or self._id

    @property
    def role(self):
        """Return object role."""
        return self._extract_attr_from_tags('Role') or self._role or ''

    @property
    def name(self):
        """Return object name."""
        return self._extract_attr_from_tags('Name') or self._name or ''

    def create_tags(self):
        """Create object tags."""
        if self.name:
            tags = self._prepare_tag_attributes_for('name')

            if self.role:
                tags = tags + self._prepare_tag_attributes_for('role')

            self.ec2_conn.create_tags(
                Resources=[self.instance_id],
                Tags=tags
            )

    def _prepare_tag_attributes_for(self, attr):
        """Prepare tag attributes."""
        return [{
            'Key': attr.title(),
            'Value': getattr(self, attr)
        }]

    def _extract_id(self):
        """Extract id from metadata."""
        if self.metadata:
            return self.metadata.get(
                self.__class__.__name__.title() + 'Id',
                None
            )
        else:
            return None

    def _extract_attr_from_tags(self, attr):
        """Extract tags."""
        if self._tag_exists():
            return [t['Value']
                    for t in self.metadata['Tags']
                    if t['Key'] == attr][0]
        else:
            return None

    def _tag_exists(self):
        """Check if tag exists."""
        return self.metadata and self.metadata.get('Tags', None)
