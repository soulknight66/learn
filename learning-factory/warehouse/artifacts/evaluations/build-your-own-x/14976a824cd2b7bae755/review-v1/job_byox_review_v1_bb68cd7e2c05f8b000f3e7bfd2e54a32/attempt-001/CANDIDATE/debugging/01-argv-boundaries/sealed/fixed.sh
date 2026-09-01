#!/usr/bin/env bash
set -u

forward_run() {
    local isolator=$1
    local rootfs=$2
    local command=$3
    shift 3
    "$isolator" "$rootfs" "$command" "$@"
}

if (($# < 3)); then
    printf 'usage: fixed.sh ISOLATOR ROOTFS COMMAND [ARG...]\n' >&2
    exit 2
fi
forward_run "$@"

