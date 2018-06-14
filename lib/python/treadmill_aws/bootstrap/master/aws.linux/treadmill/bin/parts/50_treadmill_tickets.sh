#!/bin/sh

export KRB5CCNAME={{ treadmill_host_ticket }}

{{ treadmill }}/bin/treadmill sproc tickets fetch \
    --tkt-spool-dir /treadmill/spool/tickets      \
    --appname master                              \
    --sleep 0
