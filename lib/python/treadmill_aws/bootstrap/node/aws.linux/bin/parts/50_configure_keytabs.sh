#!/bin/sh

# Configure host and HTTP keytabs.

KT_SPLIT="{{ _alias.kt_split }}"
LS="{{ _alias.ls }}"
MKDIR="{{ _alias.mkdir }}"

function fetch_all_treadmill_vip_keytabs {

    # TODO: implement fetching keytabs for the VIPs
    ${MKDIR} -vp {{ dir }}/spool/keytabs
    ${KT_SPLIT} \
        -d"{{ dir }}/spool/keytabs" \
        "/etc/krb5.keytab"

    ${LS} -al "{{ dir }}/spool/keytabs"
}

fetch_all_treadmill_vip_keytabs
