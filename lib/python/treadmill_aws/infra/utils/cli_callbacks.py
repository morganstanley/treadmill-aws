"""Validate CLI parameters."""

import re

import pkg_resources
import click

from treadmill_aws.infra import constants
from treadmill_aws.infra import vpc


_IPA_PASSWORD_RE = re.compile('.{8,}')
_URL_RE = re.compile('https?|www.*')


def convert_to_vpc_id(ctx, param, value):
    """Returns VPC ID from Name"""
    del ctx
    del param
    if not value:
        return value

    try:
        return vpc.VPC.get_id_from_name(value)
    except ValueError as ex:
        raise click.BadParameter(ex.__str__())


def validate_vpc_name(ctx, param, value):
    """Validate VPC name."""
    del ctx
    del param
    _vpc_id = vpc.VPC.get_id_from_name(value)
    if _vpc_id:
        raise click.BadParameter(
            'VPC %s already exists with name: %s' %
            (_vpc_id, value)
        )
    else:
        return value


def validate_ipa_password(ctx, param, value):
    """IPA admin password valdiation"""
    del ctx
    del param
    value = value or click.prompt(
        'IPA admin password ', hide_input=True, confirmation_prompt=True
    )
    if not _IPA_PASSWORD_RE.match(value):
        raise click.BadParameter(
            'Password must be greater than 8 characters.'
        )
    return value


def validate_domain(ctx, param, value):
    """Cloud domain validation"""
    del ctx
    del param
    if value.count(".") != 1:
        raise click.BadParameter('Valid domain like example.com')

    return value


def ipa_password_prompt(ctx, param, value):
    """IPA admin password prompt"""
    del ctx
    del param
    return value or click.prompt('IPA admin password ', hide_input=True)


def create_release_url(ctx, param, value):
    """Treadmill current release version"""
    del ctx
    del param
    if value and _URL_RE.match(value):
        return value

    def _build_url(version):
        return '{}/{}/treadmill'.format(
            constants.TREADMILL_DEFAULT_URL, version,
        )

    if value:
        return _build_url(value)

    version = None

    try:
        version = pkg_resources.resource_string(
            'treadmill',
            'VERSION.txt'
        )
    except Exception:  # pylint: disable=broad-except
        pass

    if version:
        return _build_url(version.decode('utf-8').strip())
    else:
        raise click.BadParameter('No version specified in VERSION.txt')
