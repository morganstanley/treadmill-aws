"""AWS CLI handler."""

import pprint
import logging

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import hostmanager


_LOGGER = logging.getLogger(__name__)


def init():
    """AWS CLI module"""

    @click.group()
    def aws():
        """Manage AWS instances"""
        pass

    @aws.group()
    def host():
        """Configure EC2 Objects"""
        pass

    @host.command(name='create')
    @click.option('--ami', required=True, help='AMI image ID')
    @click.option('--count', required=True, default=1, type=int,
                  help='Number of instances')
    @click.option('--key', required=True, help='Instance SSH key name')
    @click.option('--proxy', required=True, help='Proxy URL')
    @click.option('--role', required=True, default="Node",
                  help='Instance role')
    @click.option('--secgroup', required=True,
                  help='Instance security group ID')
    @click.option('--size', required=True, default='t2.small',
                  help='Instance EC2 size')
    @click.option('--subnet', required=True, help='AWS Subnet ID')
    @cli.ON_CLI_EXCEPTIONS
    def create_host(ami, count, key, proxy, role,
                    secgroup, size, subnet):
        """Create Treadmill Host(s)"""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2
        ipa_domain = awscontext.GLOBAL.ipa_domain

        hostname = hostmanager.create_host(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            image_id=ami,
            count=count,
            domain=ipa_domain,
            key=key,
            proxy=proxy,
            role=role,
            secgroup_ids=secgroup,
            instance_type=size,
            subnet_id=subnet
        )
        click.echo(pprint.pprint(hostname))

    @host.command(name='delete')
    @click.option('-h', '--hostnames', multiple=True, required=True,
                  help='Hostnames to remove from AWS and IPA')
    @cli.ON_CLI_EXCEPTIONS
    def delete_hosts(hostnames):
        """Delete Treadmill Host(s)"""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2

        hostmanager.delete_hosts(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            hostnames=hostnames
        )

    @host.command(name='list')
    @click.option('-p', '--pattern', help='Whole or partial hostname')
    @cli.ON_CLI_EXCEPTIONS
    def list_(pattern):
        """List Treadmill Host(s)"""
        ipa_client = awscontext.GLOBAL.ipaclient

        hostnames = hostmanager.find_hosts(
            ipa_client=ipa_client,
            pattern=pattern
        )
        pprint.pprint(hostnames)

    return aws
