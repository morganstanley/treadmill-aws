"""Manage AWS docker runtime.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

_LOGGER = logging.getLogger(__name__)


def prepare_env(_newroot, _app, _config):
    """Prepare docker runtime environment
    """
    _LOGGER.info('Do nothing for docker prepare_env')
