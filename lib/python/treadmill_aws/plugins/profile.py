"""AWS profile plugin.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os


def api_scope():
    """Returns admin API DNS scope."""
    return [os.environ.get('TREADMILL_CELL', 'na') + '.' + 'cell']


PROFILE = {
    'api_scope': api_scope()
}
