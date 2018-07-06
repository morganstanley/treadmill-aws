#!/bin/sh

SCRIPT_NAME="${0##*/}"
SCRIPT_DIR="${0%/$SCRIPT_NAME}"

{{ mount }} --make-rprivate /
exec {{ pid1 }} -m -p "${SCRIPT_DIR}/run_real.sh"
