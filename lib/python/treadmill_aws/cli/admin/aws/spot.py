"""Implementation of treadmill admin EC2 vpc.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import click
import jmespath

from treadmill import cli

import treadmill_aws
from treadmill_aws import awscontext
from treadmill_aws import ec2client
from treadmill_aws import hostmanager


def init():
    """EC2 spot CLI group"""
    formatter = cli.make_formatter('aws_spot')

    @click.group()
    def spot():
        """Manage spot configuration"""
        pass

    @spot.command(name='list')
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def _list():
        """List spot instance requestss"""
        ec2_conn = awscontext.GLOBAL.ec2
        sirs = [vars(o) for o in ec2client.list_spot_requests(ec2_conn)]
        if not sirs:
            print("No spot request was found")
            return
        cli.out(formatter(sirs))

    @spot.command()
    @click.argument('sir_id')
    @treadmill_aws.cli.admin.aws.ON_AWS_EXCEPTIONS
    def delete(sir_id):
        """Delete spot instance request"""
        ipa_client = awscontext.GLOBAL.ipaclient
        ec2_conn = awscontext.GLOBAL.ec2
        for item in ec2client.list_spot_requests(ec2_conn):
            if item.id == sir_id:
                sir = item
                break
        else:
            print("SIR %s was not found" % sir_id)
            return

        instances = ec2_conn.describe_instances(InstanceIds=[sir.instance_id])
        hostname = jmespath.search(
            "Reservations[].Instances[].[Tags[?Key=='Name'].Value][][]",
            instances)[0]
        print("Terminating", hostname)
        hostmanager.delete_hosts(
            ipa_client=ipa_client,
            ec2_conn=ec2_conn,
            hostnames=[hostname]
        )
        print("Cancelling", sir.id)
        ec2_conn.cancel_spot_instance_requests(
            SpotInstanceRequestIds=[sir.id])

    del _list
    del delete

    return spot
