"""Manage cloud-init userdata."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import sys
import os
import gzip
import logging
import collections
import yaml

import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


_LOGGER = logging.getLogger(__name__)


_SUFFIX_2_MIMETYPE = {
    'include-once': 'text/x-include-once-url',
    'include': 'text/x-include-url',
    'upstart-job': 'text/upstart-job',
    'yml': 'text/cloud-config',
    'yaml': 'text/cloud-config',
    'part-handler': 'text/part-handler',
    'sh': 'text/x-shellscript',
    'cloud-boothook': 'text/cloud-boothook',
}

# Match content to mime-type
#
# TODO: x-inclnude-once is missing, not clear what it should start with.
_PAYLOAD_2_MIMETYPE = {
    '#cloud-config': 'text/cloud-config',
    '#upstart-job': 'text/upstart-job',
    '#cloud-boothook': 'text/cloud-boothook',
    '#part-handler': 'text/part-handler',
    '#!': 'text/x-shellscript',
    '#include': 'text/x-include-url',
}

# cloud-init multi part is constricted in the order below.
#
# It is assumed that each part within the given type does not depend on the
# running order. If there is dependency in the scripts or data, larger script
# or data should be written.
_PARTS_ORDER = [
    'text/cloud-boothook',
    'text/part-handler',
    'text/cloud-config',
    'text/x-include-once-url',
    'text/x-include-url',
    'text/cloud-config-archive',
    'text/x-shellscript',
]


def _guess_content_type(payload):
    """Guess cloud-init content type based on content."""
    for begins_with, content_type in _PAYLOAD_2_MIMETYPE.items():
        if payload.startswith(begins_with):
            return content_type

    return None


def _iterate_cloud_init(content):
    """Read the cloud_init script, and iterate over parts.

    File can be mutli-part or just plan text file.
    """
    msg = email.message_from_string(content)
    for part in msg.walk():
        content_type = part.get_content_type()
        if content_type.startswith('multipart'):
            continue

        # Get payload as string
        payload = part.get_payload(decode=True).decode()
        if content_type is None or content_type == 'text/plain':
            content_type = _guess_content_type(payload)
            if not content_type:
                _LOGGER.warning(
                    'Unable to detect content type: %s', payload[:30]
                )
                continue

        name = part.get_filename()
        if not name:
            name = '-'

        yield (name, content_type, payload)


class CloudInit(object):
    """Manage cloud-init data."""

    def __init__(self, content=None):
        self.content_by_mimetype = collections.defaultdict(list)

        if content:
            for name, content_type, payload in _iterate_cloud_init(content):
                self.content_by_mimetype[content_type].append((name, payload))

    def userdata(self):
        """Return cloud-init compressed and encoded."""
        return gzip.compress(self.as_bytes())

    def as_str(self):
        """Render as string."""
        return self.as_bytes(encode=False).decode()

    def as_bytes(self, encode=True):
        """Render all parts as multipart message in correct order."""
        combined_message = MIMEMultipart()
        encoding = sys.getdefaultencoding()
        if not encode:
            encoding = None

        for mime_type in _PARTS_ORDER:
            for name, payload in self.content_by_mimetype.get(mime_type, []):
                # strip text/ prefix from the mimetype, as MIMEText will
                # prepend it.
                if mime_type.startswith('text/'):
                    mime_type = mime_type[len('text/'):]

                sub_message = MIMEText(
                    payload,
                    mime_type,
                    encoding,
                )
                sub_message.add_header(
                    'Content-Disposition',
                    'attachment; filename="{}"'.format(os.path.basename(name))
                )
                combined_message.attach(sub_message)

        return combined_message.as_bytes()

    def add(self, content):
        """Add payload."""
        for name, content_type, payload in _iterate_cloud_init(content):
            self.content_by_mimetype[content_type].append((name, payload))

    def add_cloud_config(self, obj):
        """Add object as cloud-config payload."""
        content = '#cloud-config\n\n{}'.format(yaml.dump(obj))
        self.content_by_mimetype['text/cloud-config'].append(('-', content))
