"""Common AWS helper functions."""


class NotUniqueError(Exception):
    """Error indicating that selection criteria is not unique."""
    pass


class NotFoundError(Exception):
    """Error indicating that selected resource was not found."""
    pass


def build_tags_filter(tags):
    """Build tag filter based on dict of tags.

    Each entry in the match is either single tag or tag list.
    It if is a list, it is "or".
    """
    filters = []
    for name, values in tags.items():
        if isinstance(values, str):
            values = [values]
        filters.append({'Name': 'tag:{}'.format(name), 'Values': values})
    return filters


def build_tags(hostname, role, version=None):
    """Create list of AWS tags from manifest."""
    if not version:
        version = ''

    tags = [{'Key': 'Name', 'Value': hostname.lower()},
            {'Key': 'Role', 'Value': role.lower()},
            {'Key': 'Version', 'Value': version.lower()}]
    return [{'ResourceType': 'instance', 'Tags': tags}]
