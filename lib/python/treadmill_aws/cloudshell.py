"""Cloudshell SSO
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import base64
import getpass
import json
import logging
import os
import random
import subprocess
import sys
import tempfile
import yaml

import click

from treadmill import dnsutils
from treadmill import gssapiprotocol

_LOGGER = logging.getLogger(__name__)


def _from_srvrec(ctx, srv_name):
    dns_server = list(ctx.obj['dns_server'])
    dns_port = ctx.obj['dns_port']

    srv_records = dnsutils.srv(srv_name, [dns_server, dns_port])
    if not srv_records:
        sys.exit('No srv records for %s' % srv_name)

    random.shuffle(srv_records)
    return [tuple(server_port[:2]) for server_port in srv_records]


def _server_list(hostport_list):
    server_list = []
    hostports = hostport_list.split(',')
    for hostport in hostports:
        host, port = hostport.split(':')
        server_list.append((host, int(port)))
    return server_list


def _gssapiprotocol_loop(request, server_list, sprinc):
    """Iterate gssaprotocol service instances."""

    for server, port in server_list:
        _LOGGER.debug('Connecting to %s:%d', server, port)
        client = gssapiprotocol.GSSAPILineClient(server,
                                                 port,
                                                 '%s@%s' % (sprinc, server),
                                                 2)
        if not client.connect():
            _LOGGER.debug(
                'failed to connect to %s:%d, failing over to next server',
                server,
                port)
            continue

        client.write(request.encode('utf-8'))
        _LOGGER.debug('Sent request [%s] to %s:%d', request, server, port)
        line = client.read().decode('utf-8')
        _LOGGER.debug('Received response from %s:%d', server, port)
        client.disconnect()

        response = json.loads(line)
        return response

    response = {}
    response['status'] = 'failure'
    response['result'] = {}
    response['result']['why'] = 'unable to connect to any servers'
    return response


def _ipa525_fetch(ctx, user, krb5_realm, krbcc=None):
    """Fetch ipa credentials."""

    request = user

    if ctx.obj['ipa525_server']:
        server_list = _server_list(ctx.obj['ipa525_server'])
    else:
        if ctx.obj['ipa525_srv_name']:
            srv_name = ctx.obj['ipa525_srv_name']
            if isinstance(ctx.obj['dns_domain'], str):
                srv_name = srv_name.replace('{dns_domain}',
                                            ctx.obj['dns_domain'])
            srv_name = srv_name.replace('{krb5_realm}', krb5_realm)
        else:
            srv_name = '_ipa525._tcp.%s' % krb5_realm
        _LOGGER.debug('ipa525 srv_name: %s', srv_name)
        server_list = _from_srvrec(ctx, srv_name)

    _LOGGER.debug('ipa525 request: %r', server_list)
    sprinc = ctx.obj['ipa525_sprinc']
    response = _gssapiprotocol_loop(request, server_list, sprinc)

    if krbcc:
        ccdir = os.path.dirname(krbcc)
    else:
        ccdir = None

    if response['status'] == 'success':
        _LOGGER.debug('ipa525 request succeeded')
        ticket_data = base64.standard_b64decode(
            response['result']['credential'])
        with tempfile.NamedTemporaryFile(delete=False,
                                         dir=ccdir,
                                         prefix='krb5cc_cloudshell_',
                                         mode='wb') as cc:
            cc.write(ticket_data)
            if krbcc:
                os.rename(cc.name, krbcc)
            else:
                krbcc = cc.name
            _LOGGER.debug('krb credential written to %s', krbcc)

    else:
        click.echo(yaml.dump(response, default_flow_style=False),
                   err=True, nl=False)
        sys.exit(1)

    return krbcc


def _ipa525_login(ctx, user, krb5_realm, krbcc):
    """Fetch ipa credentials and spawn shell."""

    if krbcc:
        _ipa525_fetch(ctx, user, krb5_realm, krbcc)
    else:
        krbcc = _ipa525_fetch(ctx, user, krb5_realm)

    if 'KRB5CCNAME' in os.environ:
        os.environ['CLOUDSHELL_KRB5CCNAME_SAVED'] = os.environ['KRB5CCNAME']

    os.environ['KRB5CCNAME'] = 'FILE:%s' % krbcc
    os.environ['CLOUDSHELL_KRB5_REALM_SAVED'] = krb5_realm

    return krbcc


def _ipa525_refresh(ctx):
    """Refresh ipa credentials."""

    user = os.environ['CLOUDSHELL_USER_SAVED']
    krb5_realm = os.environ['CLOUDSHELL_KRB5_REALM_SAVED']

    krbcc = os.environ['KRB5CCNAME'].split(':')[1]

    os.environ['KRB5CCNAME'] = os.environ['CLOUDSHELL_KRB5CCNAME_SAVED']
    _ipa525_fetch(ctx, user, krb5_realm, krbcc)
    os.environ['KRB5CCNAME'] = 'FILE:%s' % krbcc


def _awscredential_fetch(ctx, user, account, awscc=None):
    """Fetch aws credentials."""

    request = user

    if ctx.obj['awscredential_server']:
        server_list = _server_list(ctx.obj['awscredential_server'])
    else:
        if ctx.obj['awscredential_srv_name']:
            srv_name = ctx.obj['awscredential_srv_name']
            if isinstance(ctx.obj['dns_domain'], str):
                srv_name = srv_name.replace('{dns_domain}',
                                            ctx.obj['dns_domain'])
            srv_name = srv_name.replace('{aws_account}', account)
        else:
            srv_name = '{}.{}'.format('_awscredential._tcp', account)
            if ctx.obj['dns_domain']:
                srv_name = srv_name + '.' + ctx.obj['dns_domain']
        _LOGGER.debug('awscredential srv_name: %s', srv_name)
        server_list = _from_srvrec(ctx, srv_name)

    _LOGGER.debug('awscredential request: %r', server_list)
    sprinc = ctx.obj['awscredential_sprinc']
    response = _gssapiprotocol_loop(request, server_list, sprinc)

    if awscc:
        ccdir = os.path.dirname(awscc)
    else:
        ccdir = None

    if response['status'] == 'success':
        _LOGGER.debug('awscredential request succeeded')
        result = response['result']
        credfile = tempfile.NamedTemporaryFile(
            delete=False,
            dir=ccdir,
            prefix='awscc_cloudshell_')
        credfile.write(bytes(
            '[default]\n',
            'UTF-8'))
        credfile.write(bytes(
            'aws_access_key_id=%s\n' %
            result['Credentials']['AccessKeyId'],
            'UTF-8'))
        credfile.write(bytes(
            'aws_secret_access_key=%s\n' %
            result['Credentials']['SecretAccessKey'],
            'UTF-8'))
        credfile.write(bytes(
            'aws_session_token=%s\n' %
            result['Credentials']['SessionToken'],
            'UTF-8'))
        credfile.write(bytes(
            'ms_profile=%s\n' % result['Profile'],
            'UTF-8'))
        credfile.write(bytes(
            'ms_expiration=%s\n' % result['Credentials']['Expiration'],
            'UTF-8'))
        credfile.close()

        if awscc:
            os.rename(credfile.name, awscc)
            _LOGGER.debug('aws credential written to %s', awscc)
            return awscc
        else:
            _LOGGER.debug('aws credential written to %s', credfile.name)
            return credfile.name
    else:
        click.echo(yaml.dump(response, default_flow_style=False),
                   err=True, nl=False)
        sys.exit(1)


def _awscredential_login(ctx, user, account, awscc):
    """Get aws credentials."""

    if awscc:
        _awscredential_fetch(ctx, user, account, awscc)
    else:
        awscc = _awscredential_fetch(ctx, user, account)

    os.environ['AWS_SHARED_CREDENTIALS_FILE'] = awscc
    os.environ['CLOUDSHELL_AWS_ACCOUNT_SAVED'] = account
    return awscc


def _awscredential_refresh(ctx):
    """Refresh aws credentials."""

    user = os.environ['CLOUDSHELL_USER_SAVED']
    account = os.environ['CLOUDSHELL_AWS_ACCOUNT_SAVED']
    awscc = os.environ['AWS_SHARED_CREDENTIALS_FILE']

    _awscredential_fetch(ctx, user, account, awscc)


@click.group()
@click.option('--awscredential-server',
              envvar='CLOUDSHELL_AWSCREDENTIAL_SERVER',
              required=False,
              help='awscredential server.')
@click.option('--awscredential-srv-name',
              envvar='CLOUDSHELL_AWSCREDENTIAL_SRV_NAME',
              help='awscredential srv record name.')
@click.option('--awscredential-sprinc',
              envvar='CLOUDSHELL_AWSCREDENTIAL_SPRINC',
              required=False,
              default='host',
              help='awscredential krb5 sprinc name')
@click.option('--ipa525-server',
              envvar='CLOUDSHELL_IPA525_SERVER',
              required=False,
              help='ipa525 server.')
@click.option('--ipa525-srv-name',
              envvar='CLOUDSHELL_IPA525_SRV_NAME',
              help='ipa525 srv record name')
@click.option('--ipa525-sprinc',
              envvar='CLOUDSHELL_IPA525_SPRINC',
              required=False,
              default='host',
              help='IPA525 krb5 sprinc name')
@click.option('--dns-domain',
              envvar='CLOUDSHELL_DNS_DOMAIN',
              required=False,
              help='DNS domain to query srv records.')
@click.option('--dns-server',
              envvar='CLOUDSHELL_DNS_SERVER',
              required=False,
              multiple=True,
              help='DNS server to query ipa525/awscredential SRV records.')
@click.option('--dns-port',
              envvar='CLOUDSHELL_DNS_PORT',
              type=click.IntRange(0, 65535),
              default=53,
              help='DNS server port to ipa525/awscredential SRV records.')
@click.option('--debug/--no-debug',
              envvar='CLOUDSHELL_DEBUG',
              required=False,
              default=False,
              help='run in debug/verbose mode')
@click.pass_context
def cloudshell(ctx,
               awscredential_server,
               awscredential_srv_name,
               awscredential_sprinc,
               ipa525_server,
               ipa525_srv_name,
               ipa525_sprinc,
               dns_domain,
               dns_server,
               dns_port,
               debug):
    """Cloudshell SSO."""
    ctx.obj['awscredential_server'] = awscredential_server
    ctx.obj['awscredential_srv_name'] = awscredential_srv_name
    ctx.obj['awscredential_sprinc'] = awscredential_sprinc
    ctx.obj['ipa525_server'] = ipa525_server
    ctx.obj['ipa525_srv_name'] = ipa525_srv_name
    ctx.obj['ipa525_sprinc'] = ipa525_sprinc
    ctx.obj['dns_server'] = dns_server
    ctx.obj['dns_port'] = dns_port
    ctx.obj['dns_domain'] = dns_domain
    if debug:
        logging.basicConfig(level=logging.DEBUG)


@cloudshell.command(name='fetch')
@click.option('--user',
              envvar='CLOUDSHELL_USER',
              default=getpass.getuser(),
              help='user (default is %s).' % getpass.getuser())
@click.option('--krb5-realm',
              envvar='CLOUDSHELL_KRB5_REALM',
              required=False,
              help='IPA/Kerberos realm name.')
@click.option('--krbcc',
              required=False,
              help='kerberos ticket file (destination).')
@click.option('--aws-account',
              envvar='CLOUDSHELL_AWS_ACCOUNT',
              required=False,
              help='AWS Account name.')
@click.option('--awscc',
              required=False,
              help='aws credential file (destination).')
@click.pass_context
def cloudshell_fetch(ctx, user, krb5_realm, krbcc, aws_account, awscc):
    """Fetch credentials."""

    if not krb5_realm and not aws_account:
        sys.exit(
            'must specify either --krb5-realm or --aws-account (or both).')

    if krb5_realm:
        if not krbcc:
            sys.exit('--krb5-realm requires --krbcc.')
        _ipa525_fetch(ctx, user, krb5_realm, krbcc)

    if aws_account:
        if not awscc:
            sys.exit('--aws-account requires --awscc.')
        _awscredential_fetch(ctx, user, aws_account, awscc)


@cloudshell.command(name='login')
@click.option('--user',
              envvar='CLOUDSHELL_USER',
              default=getpass.getuser(),
              help='user (default is %s).' % getpass.getuser())
@click.option('--krb5-realm',
              envvar='CLOUDSHELL_KRB5_REALM',
              required=False,
              help='IPA/Kerberos realm name.')
@click.option('--krbcc',
              required=False,
              help='krb5 credential file (destination).')
@click.option('--aws-account',
              envvar='CLOUDSHELL_AWS_ACCOUNT',
              required=False,
              help='AWS Account name.')
@click.option('--awscc',
              required=False,
              help='aws credential file (destination).')
@click.argument('command', nargs=-1)
@click.pass_context
def cloudshell_login(ctx,
                     user,
                     krb5_realm,
                     krbcc,
                     aws_account,
                     awscc,
                     command):
    """Fetch credentials and spawn shell."""

    if 'CLOUDSHELL' in os.environ:
        sys.exit('"login" inside cloudshell? Did you mean "refresh"?')

    if not krb5_realm and not aws_account:
        sys.exit(
            'ERROR: must specify --krb5-realm or --aws-account (or both).')

    if krb5_realm:
        krbcc = _ipa525_login(ctx, user, krb5_realm, krbcc)

    if aws_account:
        awscc = _awscredential_login(ctx, user, aws_account, awscc)

    if not command:
        command = [os.environ['SHELL']]

    os.environ['CLOUDSHELL'] = '1'
    os.environ['CLOUDSHELL_USER_SAVED'] = user

    _LOGGER.debug('spawning command [%s]', ' '.join(command))
    subprocess.call(list(command))

    if awscc:
        _LOGGER.debug('deleting AWS credential %s', awscc)
        os.unlink(awscc)

    if krbcc:
        _LOGGER.debug('deleting krb5 credential %s', krbcc)
        os.unlink(krbcc)


@cloudshell.command(name='refresh')
@click.pass_context
def cloudshell_refresh(ctx):
    """Refresh credentials from spawned shell."""

    if 'CLOUDSHELL' not in os.environ:
        sys.exit('"refresh" from outside of cloudshell? Did you mean "login"?')

    if 'CLOUDSHELL_KRB5_REALM_SAVED' in os.environ:
        _ipa525_refresh(ctx)

    if 'CLOUDSHELL_AWS_ACCOUNT_SAVED' in os.environ:
        _awscredential_refresh(ctx)


def run():
    """Console entry point."""
    # Pylint complains about click signature magic.
    #
    # [E1123(unexpected-keyword-arg), run] \
    #     Unexpected keyword argument 'obj' in function call
    #
    # [E1120(no-value-for-parameter), run] \
    #     No value for argument 'ctx', 'userdata' in function call
    #
    # pylint: disable=E1120,E1123
    cloudshell(obj={})
