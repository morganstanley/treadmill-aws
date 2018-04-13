import click
import pprint
import logging

from treadmill_aws.infra import connection
from treadmill import cli
from treadmill_aws.aws.manager import HostManager


_LOGGER = logging.getLogger(__name__)


def init():
    """AWS CLI module"""

    @click.group()
    @click.option('-d', '--domain',
                  envvar='TREADMILL_DNS_DOMAIN',
                  help='Domain for hosted zone')
    @click.option('--cert', default='/etc/ipa/ca.crt',
                  help='freeIPA CA Cert Location')
    @click.pass_context
    def aws(ctx, cert, domain):
        """Manage AWS instances"""
        if not domain:
            click.echo('Please specify a domain')
            exit(1)

        ctx.obj['DOMAIN'] = domain
        ctx.obj['IPACERT'] = cert
        ctx.obj['host_manager'] = HostManager()

    @aws.group()
    @click.pass_context
    def host(ctx):
        """Configure EC2 Objects"""

    @host.command(name='create')
    @click.option('--ami', required=True, help='AMI image ID')
    @click.option('--count', required=True, default=1, type=int,
                  help='Number of instances')
    @click.option('--key', required=True, help='Instance SSH key name')
    @click.option('--proxy', required=True, help='Proxy URL')
    @click.option('--region', envvar='AWS_DEFAULT_REGION',
                  help='AWS Region')
    @click.option('--role', required=True, default="Node",
                  help='Instance role')
    @click.option('--secgroup', required=True,
                  help='Instance security group ID')
    @click.option('--size', required=True, default='t2.small',
                  help='Instance EC2 size')
    @click.option('--subnet', required=True, help='AWS Subnet ID')
    @click.pass_context
    @cli.ON_CLI_EXCEPTIONS
    def create_host(ctx, ami, count, key, proxy, region, role,
                    secgroup, size, subnet):
        """Create Treadmill Host(s)"""
        cert = ctx.obj['IPACERT']
        domain = ctx.obj['DOMAIN']
        manager = ctx.obj['host_manager']

        if region:
            connection.Connection.context.region_name = region
        connection.Connection.context.domain = domain

        click.echo(pprint.pprint(manager.create_host(image_id=ami,
                                                     cert=cert,
                                                     count=count,
                                                     domain=domain,
                                                     key=key,
                                                     proxy=proxy,
                                                     role=role,
                                                     secgroup_ids=secgroup,
                                                     instance_type=size,
                                                     subnet_id=subnet)))

    @host.command(name='delete')
    @click.option('-h', '--hostnames', multiple=True, required=True,
                  help='Hostnames to remove from AWS and IPA')
    @click.pass_context
    @cli.ON_CLI_EXCEPTIONS
    def delete_hosts(ctx, hostnames):
        """Delete Treadmill Host(s)"""
        cert = ctx.obj['IPACERT']
        manager = ctx.obj['host_manager']

        click.echo(manager.delete_hosts(cert=cert, hostnames=hostnames))

    @host.command(name='list')
    @click.option('-p', '--pattern', help='Whole or partial hostname')
    @click.pass_context
    @cli.ON_CLI_EXCEPTIONS
    def get_hosts(ctx, pattern):
        """List Treadmill Host(s)"""
        cert = ctx.obj['IPACERT']
        manager = ctx.obj['host_manager']

        if pattern:
            click.echo(pprint.pprint(manager.find_hosts(cert=cert,
                                                        pattern=pattern)))
        else:
            click.echo(pprint.pprint(manager.find_hosts(cert=cert)))

    return aws
