"""Load instance metadata."""

# Credits:
#
# https://gist.github.com/iMilnb => meta2dict

import json
import socket

import requests

from six.moves import http_client


def _connect():
    """Check if metadata is up."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)

    try:
        sock.connect(('169.254.169.254', 80))
        sock.close()
        return True
    except socket.error:
        return False


def load(dynamic=False):
    """Load metadata into object."""
    if not _connect():
        return {}

    metaurl = 'http://169.254.169.254/latest'
    metadata = {'meta-data': {}, 'user-data': {}}
    if dynamic:
        metadata['dynamic'] = {}

    for key in metadata:
        _load_url('{}/{}'.format(metaurl, key), metadata[key])

    return metadata


def _load_url(url, data):
    """Recursively load metadata into dictionary."""
    resp = requests.get(url)
    if resp.status_code == http_client.NOT_FOUND:
        return

    for line in resp.text.splitlines():
        if not line:
            continue
        next_url = '{}/{}'.format(url, line)
        if line.endswith('/'):
            newkey = line.split('/')[-2]
            data[newkey] = {}
            _load_url(next_url, data[newkey])
        else:
            resp = requests.get(next_url)
            if resp.status_code == http_client.OK:
                try:
                    data[line] = json.loads(resp.text)
                except ValueError:
                    data[line] = resp.text
            else:
                data[line] = None


class Metadata:
    """Lazily loads instance metadata."""

    __slots__ = (
        '_data',
        '_loaded',
    )

    def __init__(self):
        self._data = None
        self._loaded = False

    @property
    def metadata(self):
        """Return instance metadata."""
        if self._loaded:
            return self._data.get('meta-data', None)

        self._data = load()
        self._loaded = True
        return self._data.get('meta-data', {})

    @property
    def userdata(self):
        """Return instance userdata."""
        if self._loaded:
            return self._data.get('user-data', None)

        self._data = load()
        self._loaded = True
        return self._data.get('user-data', {})

    @property
    def dynamic(self):
        """Return instance dynamic data."""
        if self._loaded:
            return self._data.get('user-data', None)

        self._data = load(dynamic=True)
        self._loaded = True
        return self._data.get('user-data', {})


GLOBAL = Metadata()


def subnet_id():
    """Return subnet-id from the metadata.

    There can be multiple subnets associated with the host. Return subnet-id
    iff there is only single subnet, otherwise return None.
    """
    # TODO: is it correct that host can be in multiple subnets?
    try:
        macs = GLOBAL.metadata['network']['interfaces']['macs']
        ident = None
        for mac, attrs in macs.items():
            # It was set in previous iteration, there are more than one
            # macs.
            if ident is not None:
                return None
            ident = attrs['subnet-id']
        return ident
    except KeyError:
        return None


def vpc_id():
    """Return vpc-id from the metadata.

    There can be multiple vpcs associated with the host. Return vpc-id
    iff there is only single vpc, otherwise return None.
    """
    # TODO: is it correct that host can be in multiple vpcs?
    try:
        macs = GLOBAL.metadata['network']['interfaces']['macs']
        ident = None
        for mac, attrs in macs.items():
            # It was set in previous iteration, there are more than one
            # macs.
            if ident is not None:
                return None
            ident = attrs['vpc-id']
        return ident
    except KeyError:
        return None


def secgroup_id():
    """Return security-group-ids from the metadata.

    There can be multiple subnets associated with the host. Return subnet-id
    iff there is only single subnet, otherwise return None.
    """
    # TODO: is it correct that host can be in multiple subnets?
    try:
        macs = GLOBAL.metadata['network']['interfaces']['macs']
        ident = None
        for mac, attrs in macs.items():
            # It was set in previous iteration, there are more than one
            # macs.
            if ident is not None:
                return None
            ident = attrs['security-group-ids']
        return ident
    except KeyError:
        return None


def image_id():
    """Return ami id of current instance."""
    return GLOBAL.metadata.get('ami-id')


def instance_id():
    """Return instance id of current instance."""
    return GLOBAL.metadata.get('instance-id')


def instance_keys():
    """Return instance SSH key name."""
    public_keys = GLOBAL.metadata.get('public-keys')
    names = []
    for key in public_keys:
        idx, name = key.split('=')
        names.append(name)
    return names
