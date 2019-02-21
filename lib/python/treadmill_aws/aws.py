"""Common AWS helper functions.
"""
import functools
import logging
import time

from datetime import datetime


_LOGGER = logging.getLogger(__name__)


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


def datetime_from_suffix(word, base=16, symbol=None):
    """Convert an alphanumerical string into a datetime object
    """
    if not symbol:
        symbol = '0123456789abcdefghijklmnopqrstuvwxyz'
    if len(symbol) < 2:
        raise ValueError('Length of symbol list should be >= 2')
    if base < 2 or base > len(symbol):
        raise ValueError('Base must be in range 2-{}'.format(len(symbol)))

    number = None
    step = 0
    for char in reversed(word):
        if number not in symbol:
            raise ValueError
        if number is None:
            number = symbol.index(char) * pow(base, step)
        else:
            number += symbol.index(char) * pow(base, step)
        step += 1

    return datetime.fromtimestamp(float(number) / 10000000)


def profile(func):
    """Decorator to profile a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        res = func(*args, **kwargs)
        exec_time = time.time() - start_time
        _LOGGER.debug('%s exec time: %s', func.__name__, exec_time)
        return res
    return wrapper
