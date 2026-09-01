#!/usr/bin/env bash
set -u

if (($# != 3)); then
    printf 'usage: fixed.sh STATE_ROOT NAME ROOTFS\n' >&2
    exit 2
fi

state_root=$1
name=$2
rootfs=$3
container_dir=$state_root/containers/$name

if [[ -n ${DEBUG_READY_DIR:-} && -n ${DEBUG_RELEASE_FILE:-} ]]; then
    : >"$DEBUG_READY_DIR/$$"
    attempts=500
    while [[ ! -e $DEBUG_RELEASE_FILE && $attempts -gt 0 ]]; do
        sleep 0.01
        ((attempts -= 1))
    done
    [[ -e $DEBUG_RELEASE_FILE ]] || exit 124
fi

if ! mkdir -- "$container_dir" 2>/dev/null; then
    printf 'create: already exists\n' >&2
    exit 1
fi
if ! printf '%s\n' "$rootfs" >"$container_dir/rootfs"; then
    rm -rf -- "$container_dir"
    exit 1
fi

