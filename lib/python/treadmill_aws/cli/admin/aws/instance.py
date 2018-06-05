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
from treadmill_aws.aws import NoResourceError, DupResourceError


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
        required=False,
        help='Image',
        type=aws_cli.IMAGE
    )
    @click.option(
        '--image-account',
        required=False,
        help='AWS image account.',
    )
    @click.option(
        '--secgroup',
        required=False,
        type=aws_cli.SECGROUP,
        help='Security group'
    )
    @click.option(
        '--subnet',
        required=False,
        type=aws_cli.SUBNET,
        help='Subnet',
        multiple=True
    )
    @click.option(
        '--role',
        required=False,
        help='Instance role',
        default='generic'
    )
    @click.option(
        '--key',
        required=False,
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
        required=False,
        help='Instance data in YAML format',
        type=click.File()
    )
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def create(
            image, image_account, count, disk_size,
            key, role, secgroup, size, subnet, data):
        """Create instance(s)"""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2
        sts_conn = awscontext.GLOBAL.sts

        ipa_domain = awscontext.GLOBAL.ipa_domain

        image_id = aws_cli.admin.image_id(
            ec2_conn, sts_conn, image, image_account)
        secgroup_id = aws_cli.admin.secgroup_id(ec2_conn, secgroup)

        if data:
            instance_vars = yaml.load(stream=data)
        else:
            instance_vars = {}

        if not key:
            key = metadata.instance_keys()[0]

        total_subnets = []

        for network in subnet:
            subnet_id = aws_cli.admin.subnet_id(ec2_conn, network)
            total_subnets.append(
                ec2client.list_subnets(ec2_conn, subnet_id.split())
            )

        for network in total_subnets:
            filter_subnets = [
                net[0]['SubnetId'] for net in total_subnets
                if network[0]['SubnetId'] == net[0]['SubnetId']
            ]

            if len(filter_subnets) is not 1:
                raise DupResourceError(
                    "The same subnet was specified multiple times"
                )

        ec2_cap = hostmanager.is_space_available(total_subnets)

        if ec2_cap < count:
            raise NoResourceError(
                "There are not enough IP Addresses to run %s EC2 instances"
                % count
            )

        placements = {}

        for network in total_subnets:
            availability, total = hostmanager.get_availability(network)
            placements[network[0]['SubnetId']] = (availability, total)

        best_placement = hostmanager.get_availability_rate(placements)

        hostnames = hostmanager.run_ec2(
            placements,
            best_placement,
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            image_id=image_id,
            count=count,
            disk=disk_size,
            domain=ipa_domain,
            key=key,
            secgroup_ids=secgroup_id,
            instance_type=size,
            role=role,
            instance_vars=instance_vars,
        )

        for hostname in hostnames:
            for instance in hostname:
                click.echo(instance)

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

    del _list
    del configure
    del delete

    return instance
