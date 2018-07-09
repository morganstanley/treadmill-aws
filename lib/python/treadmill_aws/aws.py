"""Common AWS helper functions."""


class NotUniqueError(Exception):
    """Error indicating that selection criteria is not unique."""
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


def int2str(number, base=16, symbol=None):
    """Convert integer to string in a given numbererical base
    """
    if not symbol:
        symbol = '0123456789abcdefghijklmnopqrstuvwxyz'
    if len(symbol) < 2:
        raise ValueError('Length of symbol list should be >= 2')
    if base < 2 or base > len(symbol):
        raise ValueError('Base must be in range 2-{}'.format(len(symbol)))

    negative = False
    if number < 0:
        negative = True
        number = -number

    number, remainder = divmod(number, base)
    basestr = ''
    while number:
        basestr = symbol[remainder] + basestr
        number, remainder = divmod(number, base)
    basestr = ('-' if negative else '') + symbol[remainder] + basestr

    return basestr
