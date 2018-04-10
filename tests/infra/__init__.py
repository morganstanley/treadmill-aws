"""Infra tests."""

from treadmill_aws.infra import connection


connection.Connection.context.region_name = 'foobar'
