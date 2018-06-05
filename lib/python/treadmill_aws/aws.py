"""Common AWS helper functions."""


class NotUniqueError(Exception):
    """Error indicating that selection criteria is not unique."""
    pass


class NoResourceError(Exception):
    """Error indicating that selection criteria has no resource."""
    pass


class DupResourceError(Exception):
    """Error indicating that selection criteria has duplicate resource."""
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
