#!/usr/bin/env bash
set -u

forward_run() {
    local isolator=$1
    local rootfs=$2
    local command=$3
    shift 3

    # Intentionally broken: diagnose this call site.
    $isolator $rootfs $command $*
}

if (($# < 3)); then
    printf 'usage: broken.sh ISOLATOR ROOTFS COMMAND [ARG...]\n' >&2
    exit 2
fi
forward_run "$@"

