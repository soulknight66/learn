#!/usr/bin/env bash
set -eu

if [ "$#" -lt 3 ]; then
    printf 'tinybox-runner: expected ROOTFS NAME COMMAND [ARG ...]\n' >&2
    exit 2
fi

rootfs=$1
name=$2
shift 2

# TODO: validate rootfs, name, and the absolute command. Then enter the namespaces described in
# REQUIREMENTS.md, change root, mount a private /proc, set the hostname, and exec "$@" directly.
printf 'tinybox-runner: namespace execution is not implemented\n' >&2
exit 70
