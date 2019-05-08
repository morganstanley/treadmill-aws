"""Garbage collector."""

import logging
import time

import click
import jmespath

from treadmill import cli
from treadmill import plugin_manager

from treadmill_aws import cli as aws_cli
from treadmill_aws import awscontext


_LOGGER = logging.getLogger(__name__)
_MODULE = 'treadmill_aws.garbage_collector'


def _ec2_instances():
    """Return a set of all ec2 instance hostnames."""
    instance_name = jmespath.compile(
        "Reservations[].Instances[].[Tags[?Key=='Name'].Value][][]"
    )

    _LOGGER.info('Fetching valid instances from AWS')
    instances = instance_name.search(
        awscontext.GLOBAL.ec2.describe_instances()
    )
    _LOGGER.debug("%d valid instances found", len(instances))

    return set(instances)


def _run_gc(gc_plugins, interval):
    """Garbage collector plugins executor."""
    plugins = {name: plugin_manager.load(_MODULE, name) for name in gc_plugins}
    servers = {name: set() for name in gc_plugins}
    while True:
        for name, plugin in plugins.items():
            servers[name] = plugin.list()

        _LOGGER.info('Snoozing for %d seconds', interval)
        time.sleep(interval)

        for name, plugin in plugins.items():
            _LOGGER.info('%s cleanup started', name.upper())
            if isinstance(servers[name], dict):
                for server in set(servers[name]) - _ec2_instances():
                    plugin.delete(server, servers[name][server])
            else:
                for server in servers[name] - _ec2_instances():
                    plugin.delete(server)
            _LOGGER.info('%s cleanup completed', name.upper())


def init():
    """Return top level command handler."""

    @click.command()
    @click.option('--interval', type=float, default=3600,
                  help='Time interval to snooze before cleanup (seconds).')
    @click.option('--list-plugins', is_flag=True,
                  help='List of available plugins.')
    @click.option('--gc-plugins', default=None, type=cli.LIST,
                  help='Comma separated list of plugins to run.')
    @click.option('--ipa-domain', required=False,
                  envvar='IPA_DOMAIN',
                  callback=aws_cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    @click.option('--ipa-certs', required=False,
                  default='/etc/ipa/ca.crt',
                  callback=aws_cli.handle_context_opt,
                  is_eager=True,
                  expose_value=False)
    def top(interval, list_plugins, gc_plugins):
        """Garbage collector top command handler."""
        if list_plugins:
            print(", ".join(plugin_manager.names(_MODULE)))
            return
        _LOGGER.info('Running garbage collector')
        _run_gc(gc_plugins or plugin_manager.names(_MODULE), interval)
        _LOGGER.info('Cleanup completed')

    return top
