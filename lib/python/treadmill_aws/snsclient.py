"""AWS SNS helper functions.
"""

import logging
from . import aws

_LOGGER = logging.getLogger(__name__)


@aws.profile
def publish_to_sns(sns_client, message, subject, topic_arn):
    """ Publishes message to SNS queue"""
    response = sns_client.publish(
        TopicArn=topic_arn,
        Message=str(message),
        Subject=str(subject),
    )
    return response


@aws.profile
def list_sns_topics(sns_client):
    """ Returns all AWS SNS topics """
    return sns_client.list_topics()
