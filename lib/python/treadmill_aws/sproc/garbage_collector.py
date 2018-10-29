"""Garbage collector plugin
"""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging
import time

import click
import jmespath

from treadmill import plugin_manager
from treadmill.cli import LIST
from treadmill_aws.cli import handle_context_opt
from treadmill_aws.awscontext import GLOBAL


_LOGGER = logging.getLogger(__name__)
_MODULE = 'treadmill_aws.garbage_collector'


def _ec2_instances():
    """Returns a set of all ec2 instance's hostname"""
    instance_name = jmespath.compile(
        "Reservations[].Instances[].[Tags[?Key=='Name'].Value][][]")

    _LOGGER.info('Fetching valid instances from AWS')
    instances = instance_name.search(GLOBAL.ec2.describe_instances())
    _LOGGER.debug("%d valid instances found", len(instances))

    return set(instances)


def _run_gc(gc_plugins, interval):
    """Garbage collector plugins executor."""

    plugins = {name: plugin_manager.load(_MODULE, name) for name in gc_plugins}
    servers = {name: set() for name in gc_plugins}
    while True:
        for name, plugin in plugins:
            servers[name] = plugin.list()

        _LOGGER.debug('snoozing for %d minutes', interval / 60)
        time.sleep(interval)

        for name, plugin in plugins:
            _LOGGER.info('%s cleanup started', name.upper())
            for server in servers[name] - _ec2_instances():
                plugin.delete(server)
            _LOGGER.info('%s cleanup complete', name.upper())


def init():
    """Return top level command handler.
    """

    @click.command()
    @click.option('--interval', type=float, default=3600,
                  help='interval in seconds')
    @click.option('--list-plugins', is_flag=True,
                  help='List of available plugins.')
    @click.option('--gc-plugins', default=None, type=LIST,
                  help='Comma separated list of plugins to run.')
    @click.option('--ipa-domain', required=False,
                  envvar='IPA_DOMAIN',
                  callback=handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    @click.option('--ipa-certs', required=False,
                  default='/etc/ipa/ca.crt',
                  callback=handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    def top(interval, list_plugins, gc_plugins):
        """Garbage Collector top command handler.
        """
        if list_plugins:
            print(", ".join(plugin_manager.names(_MODULE)))
            return
        _LOGGER.info('Running garbage collector')
        _run_gc(gc_plugins or plugin_manager.names(_MODULE), interval)
        _LOGGER.info('Cleanup completed.')

    return top
