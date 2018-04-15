"""Common AWS command line helpers.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click

from treadmill import cli

from treadmill_aws import awscontext


def handle_context_opt(ctx, param, value):
    """Handle eager CLI options to configure context.

    The eager options are evaluated directly during parsing phase, and can
    affect other options parsing (like required/not).

    The only side effect of consuming these options are setting attributes
    of the global context.
    """

    if not value or ctx.resilient_parsing:
        return None

    if value == '-':
        return None

    opt = param.name
    if opt == 'aws_region':
        awscontext.GLOBAL.region_name = value

    if opt == 'ipa_certs':
        awscontext.GLOBAL.ipa_certs = value

    if opt == 'ipa_domain':
        awscontext.GLOBAL.ipa_domain = value

    return value
