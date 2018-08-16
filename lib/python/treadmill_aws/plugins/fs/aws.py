"""Manage AWS specific filesystem layout.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import os
import stat

from treadmill import fs
from treadmill.fs import linux as fs_linux
from treadmill.runtime.linux.image import fs as image_fs

_LOGGER = logging.getLogger(__name__)


class MinimalAWSFilesystemPlugin(image_fs.FilesystemPluginBase):
    """Configure layout in chroot."""

    def init(self):
        pass

    def configure(self, container_dir, app):
        root_dir = os.path.join(container_dir, 'root')
        newroot_norm = fs.norm_safe(root_dir)

        emptydirs = [
            '/opt/s6',
            '/opt/treadmill',
            '/opt/treadmill-bind',
        ]

        stickydirs = []

        mounts = [
            '/opt/s6',
            '/opt/treadmill',
            '/opt/treadmill-bind',
        ]

        for directory in emptydirs:
            fs.mkdir_safe(newroot_norm + directory)

        for directory in stickydirs:
            os.chmod(newroot_norm + directory, 0o777 | stat.S_ISVTX)

        for mount in mounts:
            if os.path.exists(mount):
                fs_linux.mount_bind(
                    newroot_norm, mount,
                    recursive=True, read_only=True
                )
