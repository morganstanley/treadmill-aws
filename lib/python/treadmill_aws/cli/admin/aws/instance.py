"""Implementation of treadmill admin EC2 vpc.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click
import yaml

from treadmill import cli

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import hostmanager
from treadmill_aws import metadata
from treadmill_aws import cli as aws_cli


def init():
    """EC2 instance CLI group"""
    formatter = cli.make_formatter('aws_instance')

    @click.group()
    def instance():
        """Manage instance configuration"""
        pass

    @instance.command(name='list')
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def _list():
        """List instances"""
        ec2_conn = awscontext.GLOBAL.ec2
        instances = ec2client.list_instances(ec2_conn)
        cli.out(formatter(instances))

    @instance.command()
    @click.argument('instance', required=False, type=aws_cli.INSTANCE)
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def configure(instance):
        """Configure instance"""
        if not instance:
            instance = {'ids': [metadata.instance_id()]}

        ec2_conn = awscontext.GLOBAL.ec2
        instance_obj = ec2client.get_instance(ec2_conn, **instance)
        cli.out(formatter(instance_obj))

    @instance.command()
    @click.option(
        '--image',
        help='Image',
        type=aws_cli.IMAGE
    )
    @click.option(
        '--image-account',
        help='AWS image account.',
    )
    @click.option(
        '--secgroup',
        type=aws_cli.SECGROUP,
        help='Security group'
    )
    @click.option(
        '--subnet',
        type=aws_cli.SUBNET,
        help='Subnet'
    )
    @click.option(
        '--role',
        help='Instance role',
        default='generic'
    )
    @click.option(
        '--key',
        help='Instance SSH key name'
    )
    @click.option(
        '--size',
        required=True,
        default='t2.small',
        help='Instance EC2 size'
    )
    @click.option(
        '--count',
        required=True,
        default=1,
        type=int,
        help='Number of instances'
    )
    @click.option(
        '--disk-size',
        required=True,
        default='10G',
        help='Root parition size, e.g. 100G',
        callback=aws_cli.convert_disk_size_to_int
    )
    @click.option(
        '--data',
        help='Instance data in YAML format',
        type=click.File()
    )
    @click.option(
        '--instance-profile',
        help='EC2 instance profile to attach',
    )
    @click.option(
        '--hostgroup',
        multiple=True,
        help='IPA hostgroup memberships',
    )
    @click.option(
        '--hostname',
        help='Shortname or Pattern, e.g. PATTERN-{time}',
    )
    @click.option(
        '--ip-address',
        help='IP address',
    )
    @click.option(
        '--eni',
        help='Elastic Network ID; e.g. eni-xxxxxxxx',
    )
    @click.option(
        '--spot',
        is_flag=True,
        required=False,
        help='Request a spot instance',
    )
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def create(
            image, image_account, count, disk_size, key, role, ip_address, eni,
            spot, secgroup, size, subnet, data, instance_profile,
            hostgroup, hostname):
        """Create instance(s)"""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2
        sts_conn = awscontext.GLOBAL.sts

        ipa_domain = awscontext.GLOBAL.ipa_domain

        image_id = aws_cli.admin.image_id(
            ec2_conn, sts_conn, image, image_account)
        secgroup_id = aws_cli.admin.secgroup_id(ec2_conn, secgroup)
        subnet_id = aws_cli.admin.subnet_id(ec2_conn, subnet)

        if data:
            instance_vars = yaml.load(stream=data)
        else:
            instance_vars = {}

        hosts_created = hostmanager.create_host(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            image_id=image_id,
            count=count,
            disk=disk_size,
            domain=ipa_domain,
            key=key,
            secgroup_ids=secgroup_id,
            instance_type=size,
            subnet=subnet_id,
            role=role,
            instance_vars=instance_vars,
            instance_profile=instance_profile,
            hostgroups=hostgroup,
            hostname=hostname,
            ip_address=ip_address,
            eni=eni,
            spot=spot
        )
        for host_created in hosts_created:
            click.echo(host_created)

    @instance.command(name='delete')
    @click.argument('hostname')
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def delete(hostname):
        """Delete instance."""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2

        hostmanager.delete_hosts(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            hostnames=[hostname]
        )

    @instance.command(name='start')
    @click.argument('hostname', nargs=-1, required=True)
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def start(hostname):
        """Start instance(s)."""
        ec2_conn = awscontext.GLOBAL.ec2
        ec2client.start_instances(ec2_conn,
                                  state=['stopped'],
                                  hostnames=list(hostname))

    @instance.command(name='stop')
    @click.argument('hostname', nargs=-1, required=True)
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def stop(hostname):
        """Stop instance(s)."""
        ec2_conn = awscontext.GLOBAL.ec2
        ec2client.stop_instances(ec2_conn,
                                 state=['pending', 'running'],
                                 hostnames=list(hostname))

    del _list
    del configure
    del delete
    del start
    del stop

    return instance
