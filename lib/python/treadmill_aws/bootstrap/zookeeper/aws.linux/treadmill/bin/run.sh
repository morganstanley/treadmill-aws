#!/bin/sh

CHROOT={{ _alias.chroot }}
CHMOD={{ _alias.chmod }}
ECHO={{ _alias.echo }}
GREP={{ _alias.grep }}
LS={{ _alias.ls }}
MKDIR={{ _alias.mkdir }}
MOUNT={{ _alias.mount }}
RM={{ _alias.rm }}

unset KRB5CCNAME
unset KRB5_KTNAME

for SVC in $($LS {{ dir }}/treadmill/init); do
    $GREP {{ dir }}/treadmill/init/$SVC/\$ {{ dir }}/.install > /dev/null
    if [ $? != 0 ]; then
        if [ -d {{ dir }}/treadmill/init/$SVC ]; then
            $ECHO Removing extra service: $SVC
            $RM -vrf {{ dir }}/treadmill/init/$SVC
        fi
    fi
done

$RM -vf {{ dir }}/treadmill/init/*/data/exits/*
$RM -vf {{ dir }}/treadmill/tombstones/*

for DIR in $(ls -a /); do
    # Ignore . and .. directories
    if [[ "${DIR}" != "." && "${DIR}" != ".." && -d /${DIR} ]]; then
        $MKDIR -p {{ dir }}/${DIR}
        if [ $DIR == "tmp" ]; then
            # Make /tmp in chroot rw for all with sticky bit.
            $CHMOD 1777 {{ dir }}/$DIR
        fi
    fi
done

cd {{ dir }}

# Starting svscan
export PATH={{ _alias.s6 }}/bin:$PATH

exec \
    {{ _alias.s6_envdir }} {{ dir }}/treadmill/env \
    {{ _alias.s6_svscan }} {{ dir }}/treadmill/init

