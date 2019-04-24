"""Services and utilities used to send alerts through SNS
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from treadmill import admin
from treadmill import exc
from treadmill import context

from treadmill_aws import awscontext
from treadmill_aws import snsclient


_LOGGER = logging.getLogger(__name__)


def _noop():
    """Default NOOP callback"""
    pass


def send_event(
        type_=None,
        instanceid=None,
        summary=None,
        event_time=None,
        on_success_callback=_noop,
        **kwargs):
    """Send event to SNS.
    """
    admin_cell = admin.Cell(context.GLOBAL.ldap.conn)
    cell = admin_cell.get(context.GLOBAL.cell)
    data = cell['data']

    sns_alert_arn = data['sns_topic']
    if sns_alert_arn is None:
        raise exc.TreadmillError('SNS Topic ARN not found')

    message = {'type_': type_,
               'instanceid': instanceid,
               'summary': summary,
               'event_time': event_time}
    if kwargs:
        message.update(kwargs)

    success = snsclient.publish_to_sns(sns_client=awscontext.GLOBAL.sns,
                                       message=message,
                                       subject='Treadmill Alert',
                                       topic_arn=sns_alert_arn)
    if success:
        on_success_callback()
