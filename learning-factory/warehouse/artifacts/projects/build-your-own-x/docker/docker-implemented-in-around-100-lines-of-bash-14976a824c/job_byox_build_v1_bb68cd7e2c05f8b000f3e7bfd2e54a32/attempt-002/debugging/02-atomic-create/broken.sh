#!/usr/bin/env bash
set -u

if (($# != 3)); then
    printf 'usage: broken.sh STATE_ROOT NAME ROOTFS\n' >&2
    exit 2
fi

state_root=$1
name=$2
rootfs=$3
container_dir=$state_root/containers/$name

if [[ -e $container_dir ]]; then
    printf 'create: already exists\n' >&2
    exit 1
fi

# The test uses this hook to make the check/use race deterministic.
if [[ -n ${DEBUG_READY_DIR:-} && -n ${DEBUG_RELEASE_FILE:-} ]]; then
    : >"$DEBUG_READY_DIR/$$"
    attempts=500
    while [[ ! -e $DEBUG_RELEASE_FILE && $attempts -gt 0 ]]; do
        sleep 0.01
        ((attempts -= 1))
    done
    [[ -e $DEBUG_RELEASE_FILE ]] || exit 124
fi

# Intentionally broken: both contenders can report success.
mkdir -p -- "$container_dir"
printf '%s\n' "$rootfs" >"$container_dir/rootfs"

