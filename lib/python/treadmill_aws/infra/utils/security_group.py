"""Security group utilities."""

from urllib import request

from treadmill_aws.infra import connection


def _get_ip(anywhere):
    """Get IP."""
    if anywhere:
        _ip = '0.0.0.0/0'
    else:
        _ip = request.urlopen(
            'http://ip.42.pl/raw'
        ).read().decode('utf-8') + '/32'
    return _ip


def enable(port, group_id, protocol='tcp', anywhere=True):
    """Enable security group."""
    port = int(port)
    conn = connection.Connection()
    conn.authorize_security_group_ingress(
        CidrIp=_get_ip(anywhere),
        FromPort=port,
        ToPort=port,
        GroupId=group_id,
        IpProtocol=protocol
    )


def disable(port, group_id, protocol='tcp', anywhere=True):
    """Disable security group."""
    port = int(port)
    conn = connection.Connection()
    conn.revoke_security_group_ingress(
        CidrIp=_get_ip(anywhere),
        FromPort=port,
        ToPort=port,
        GroupId=group_id,
        IpProtocol=protocol
    )
