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

    assert isinstance(tags, (list, dict)), 'tags must be either list or dict.'
    if isinstance(tags, list):
        tags_dict = {tag['name']: tag['value'] for tag in tags}
    else:
        tags_dict = tags

    for name, values in tags_dict.items():
        if isinstance(values, str):
            values = [values]
        filters.append({'Name': 'tag:{}'.format(name), 'Values': values})
    return filters


# TODO: the name of the function is misleading. It is related to instance tags,
#       this should be reflected in the name of the function.
def build_tags(hostname, role, version=None):
    """Create list of AWS tags from manifest."""
    if not version:
        version = ''

    tags = [{'Key': 'Name', 'Value': hostname.lower()},
            {'Key': 'Role', 'Value': role.lower()},
            {'Key': 'Version', 'Value': version.lower()}]
    return [{'ResourceType': 'instance', 'Tags': tags}]
