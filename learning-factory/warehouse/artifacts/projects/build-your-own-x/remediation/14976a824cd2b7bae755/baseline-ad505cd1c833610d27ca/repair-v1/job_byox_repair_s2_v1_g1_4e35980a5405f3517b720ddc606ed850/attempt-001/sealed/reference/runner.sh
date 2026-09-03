#!/usr/bin/env bash
set -eu

internal_marker=__tinybox_namespace_stage__

die() {
    printf 'tinybox-runner: %s\n' "$1" >&2
    exit "${2-3}"
}

valid_name() {
    [[ ${1-} =~ ^[a-z][a-z0-9_-]{0,31}$ ]]
}

if [ "${1-}" = "$internal_marker" ]; then
    [ "$#" -ge 5 ] || die 'invalid internal invocation' 2
    rootfs=$2
    name=$3
    token=$4
    shift 4
    [ "$token" = "${TINYBOX_STAGE_TOKEN-}" ] \
        || die 'invalid namespace-stage token'
    [ -n "$token" ] || die 'empty namespace-stage token'
    [ -d "$rootfs" ] && [ ! -L "$rootfs" ] || die 'unsafe rootfs in namespace stage'
    valid_name "$name" || die 'invalid name in namespace stage'
    command -v mount >/dev/null 2>&1 || die 'mount command is unavailable' 127
    command -v hostname >/dev/null 2>&1 || die 'hostname command is unavailable' 127
    command -v chroot >/dev/null 2>&1 || die 'chroot command is unavailable' 127
    mount --make-rprivate / || die 'cannot make mount propagation private'
    hostname "$name" || die 'cannot set isolated hostname'
    mount -t proc -o nosuid,noexec,nodev proc "$rootfs/proc" \
        || die 'cannot mount the namespace proc filesystem'
    unset TINYBOX_STAGE_TOKEN
    exec chroot -- "$rootfs" "$@"
fi

[ "$#" -ge 3 ] || die 'expected ROOTFS NAME COMMAND [ARG ...]' 2
rootfs=$1
name=$2
shift 2

[ -d "$rootfs" ] && [ ! -L "$rootfs" ] || die "rootfs is not a safe directory: $rootfs"
valid_name "$name" || die "invalid container name: $name"
case "$1" in
    /*) ;;
    *) die 'command must be an absolute container path' 2 ;;
esac
command -v unshare >/dev/null 2>&1 || die 'GNU/Linux unshare is unavailable' 127

rootfs=$(CDPATH= cd -- "$rootfs" && pwd -P) || die 'cannot resolve rootfs'
if [ -L "$rootfs/proc" ] || { [ -e "$rootfs/proc" ] && [ ! -d "$rootfs/proc" ]; }; then
    die 'rootfs /proc is not a safe directory'
fi
mkdir -p -- "$rootfs/proc" || die 'cannot create rootfs /proc'

runner_path=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/$(basename -- "${BASH_SOURCE[0]}")
stage_token=$$.$RANDOM.$RANDOM
export TINYBOX_STAGE_TOKEN=$stage_token
exec unshare --user --map-root-user --mount --pid --fork --uts --ipc -- \
    "$runner_path" "$internal_marker" "$rootfs" "$name" "$stage_token" "$@"
