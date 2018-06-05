#!/bin/sh

# Ensure that /etc/ld.so.preload exists.
#
# TODO: temp workaround, until the core code is fixed to handle this condition
#       gracefully.


TOUCH="{{ _alias.touch }}"
$TOUCH /etc/ld.so.preload
