"""Implementation of treadmill admin AWS snapshot manager.
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from datetime import datetime
import logging
import time

import click

from treadmill import cli

from treadmill_aws import awscontext
from treadmill_aws import cli as aws_cli
from treadmill_aws import ec2client

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.INFO)


class SnapshotError(Exception):
    """Snapshot Exception."""
    pass


def _instance_tag(instance, tagname):
    """get name tag from instance."""

    for kv in instance['Tags']:
        if kv['Key'] == tagname:
            return kv['Value']

    return None


def _stop_instance(ec2_conn, instance, tries, interval, dry_run=False):
    """stop EC2 instance - syncrhonously."""

    _LOGGER.info('stopping instance ...')
    instance_id = instance['InstanceId']

    counter = 0
    state = None
    while counter < tries and state != 'stopped':
        counter = counter + 1
        response = ec2_conn.stop_instances(InstanceIds=[instance_id],
                                           DryRun=dry_run)
        state = response['StoppingInstances'][0]['CurrentState']['Name']
        if state == 'stopped':
            break
        _LOGGER.info('instance is currently in state [%s], polling ...', state)
        time.sleep(interval)

    if state == 'stopped':
        _LOGGER.info('instance is stopped.')
    else:
        raise SnapshotError('timed out trying to stop instance')


def _start_instance(ec2_conn, instance, tries, interval, dry_run=False):
    """start EC2 instance - syncrhonously."""

    instance_id = instance['InstanceId']

    _LOGGER.info('starting instance ...')

    counter = 0
    state = None
    while counter < tries and state != 'running':
        counter = counter + 1
        response = ec2_conn.start_instances(InstanceIds=[instance_id],
                                            DryRun=dry_run)
        state = response['StartingInstances'][0]['CurrentState']['Name']
        if state == 'running':
            break
        _LOGGER.info('instance is currently in state [%s], poll ...', state)
        time.sleep(interval)

    if state == 'running':
        _LOGGER.info('instance is running.')
    else:
        raise SnapshotError('timed out trying to start instance')


def _get_volume_id_from_instance(instance, device):
    """Get volume ID from instance and device."""

    volume_id = None
    for bdm in instance['BlockDeviceMappings']:
        if bdm['DeviceName'] == device:
            volume_id = bdm['Ebs']['VolumeId']
            break
    if not volume_id:
        raise SnapshotError('Instance has no EBS device [%s]' % device)
    return volume_id


def init():
    """Manage AWS snapshots."""

    formatter = cli.make_formatter('aws_snapshot')

    #
    # snapshots do not have names, but they have description, so we use that
    #

    @click.group()
    def snapshot():
        """Manage AWS snapshots."""
        pass

    @snapshot.command()
    @click.option('--instance',
                  type=aws_cli.INSTANCE,
                  required=True,
                  help='instance from which to take snapshot')
    @click.option('--device',
                  default='/dev/sda1',
                  help='device from which to take snapshot')
    @click.option('--reboot',
                  is_flag=True,
                  help='reboot instance if instance is running')
    @click.option('--tries',
                  type=click.INT,
                  default=10,
                  help='if rebooting, number of times to poll '
                       'state of shutdown/restart')
    @click.option('--interval',
                  type=click.INT,
                  default=10,
                  help='if rebooting, number of seconds between polls')
    @click.option('--dry-run',
                  is_flag=True,
                  default=False,
                  help='invoke aws operations with DryRun=True')
    @click.argument('name',
                    required=True)
    @cli.admin.ON_EXCEPTIONS
    def create(instance, device, reboot, tries, interval, dry_run, name):
        """Create snapshot from instance."""

        ec2_conn = awscontext.GLOBAL.ec2
        instance_obj = ec2client.get_instance(ec2_conn, **instance)

        initial_state = instance_obj['State']['Name']
        hostname = _instance_tag(instance_obj, 'Name')

        if reboot:
            if initial_state == 'running':
                _LOGGER.info('%s is in state [running], will stop instance, '
                             'take snapshot, start instance.', hostname)
                do_reboot = True
            else:
                raise SnapshotError('--reboot requires instance to be in '
                                    'state [running], instance is in '
                                    'state [%s]' % initial_state)
        else:
            if initial_state == 'stopped':
                _LOGGER.info('%s is in state [stopped], will take snapshot '
                             '(no reboot required).', hostname)
                do_reboot = False
            else:
                raise SnapshotError('instance is in state [%s], use --reboot '
                                    'to stop instance, take snapshot, then '
                                    'start instance.' % initial_state)

        if do_reboot:
            _stop_instance(ec2_conn, instance_obj, tries, interval, dry_run)

        volume_id = _get_volume_id_from_instance(instance_obj, device)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%SZ')

        sn_type = 'backup'
        desc = '%s %s %s' % (sn_type, hostname, timestamp)
        architecture = instance_obj['Architecture']
        ena_support = '%r' % instance_obj['EnaSupport']
        virtualization_type = instance_obj['VirtualizationType']
        tagspecs = [
            {
                'ResourceType': 'snapshot',
                'Tags': [
                    {'Key': 'Name', 'Value': name},
                    {'Key': 'Hostname', 'Value': hostname},
                    {'Key': 'Type', 'Value': 'backup'},
                    {'Key': 'Device', 'Value': device},
                    {'Key': 'Architecture', 'Value': architecture},
                    {'Key': 'EnaSupport', 'Value': ena_support},
                    {'Key': 'VirtualizationType',
                     'Value': virtualization_type},
                ]
            }
        ]

        kwargs = {
            'Description': desc,
            'VolumeId': volume_id,
            'TagSpecifications': tagspecs,
        }

        if dry_run:
            kwargs['DryRun'] = True

        response = ec2_conn.create_snapshot(**kwargs)

        kwargs = {'Filters': [{'Name': 'snapshot-id',
                               'Values': [response['SnapshotId']]}]}
        response = ec2_conn.describe_snapshots(**kwargs)
        cli.out(formatter(response['Snapshots'][0]))

        if do_reboot:
            _start_instance(ec2_conn, instance_obj, tries, interval, dry_run)

    @snapshot.command(name='configure')
    @cli.admin.ON_EXCEPTIONS
    @click.argument('snapshot',
                    type=aws_cli.SNAPSHOT,
                    required=True)
    def configure(snapshot):
        """Configure (show) AWS snapshot."""

        ec2_conn = awscontext.GLOBAL.ec2
        snapshot_obj = ec2client.get_snapshot(ec2_conn, **snapshot)
        cli.out(formatter(snapshot_obj))

    @snapshot.command(name='list')
    @cli.admin.ON_EXCEPTIONS
    @click.option('--match',
                  type=aws_cli.SNAPSHOT,
                  help='match on snapshot name, id, or tag (key=value).')
    def list_snapshots(match):
        """List AWS snapshots."""

        ec2_conn = awscontext.GLOBAL.ec2
        snapshots = ec2client.list_snapshots(ec2_conn, **match)
        cli.out(formatter(snapshots))

    @snapshot.command()
    @click.argument('snapshot')
    @cli.admin.ON_EXCEPTIONS
    def delete(snapshot):
        """Delete AWS snapshot."""

        ec2_conn = awscontext.GLOBAL.ec2
        response = ec2_conn.delete_snapshot(SnapshotId=snapshot)

    del configure
    del create
    del list_snapshots
    del delete
    return snapshot
