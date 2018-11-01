#!/bin/sh

CAT="{{ _alias.cat }}"
ECHO="{{ _alias.echo }}"

CGROUP_BASE="/sys/fs/cgroup"

# Get total number of CPU cores
CPUSET_ALL_CORES="$(${CAT} ${CGROUP_BASE}/cpuset/cpuset.cpus)"

# Reset CPU core assignment
${ECHO} ${CPUSET_ALL_CORES} >${CGROUP_BASE}/cpuset/system.slice/cpuset.cpus

# Reset memory limits
${ECHO} -1 >${CGROUP_BASE}/memory/system.slice/memory.limit_in_bytes
