#!/bin/sh

# Ensure that /var/lib/docker socket exists and Docker networking is disabled.
# TODO: remove untrusted registry config

(
cat <<EOF
DOCKER_NETWORK_OPTIONS=\
  --bridge=none\
  --ip-forward=false\
  --ip-masq=false\
  --iptables=false
EOF
) > /etc/sysconfig/docker-latest-network

(
cat <<EOF
[registries.search]
registries = []
[registries.insecure]
registries = ['{{ data.docker_registry }}']
[registries.block]
registries = []
EOF
) > /etc/containers/registries.conf
