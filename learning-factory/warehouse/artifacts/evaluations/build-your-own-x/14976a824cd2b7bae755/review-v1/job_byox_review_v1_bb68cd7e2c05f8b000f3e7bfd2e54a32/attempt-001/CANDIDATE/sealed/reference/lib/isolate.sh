#!/usr/bin/env bash
# Linux namespace/chroot isolation helper for minictr.
# Interface: isolate.sh ROOTFS COMMAND [ARG...]

set -uo pipefail

isolate_error() {
    printf 'minictr: isolate: %s\n' "$*" >&2
}

isolate_resolve_tool() {
    local requested=$1 resolved
    if [[ $requested == */* ]]; then
        [[ $requested == /* && -f $requested && -x $requested ]] || return 1
        printf '%s\n' "$requested"
        return 0
    fi
    resolved=$(command -v -- "$requested" 2>/dev/null) || return 1
    [[ $resolved == /* && -f $resolved && -x $resolved ]] || return 1
    printf '%s\n' "$resolved"
}

readonly ISOLATE_SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P
)"
readonly ISOLATE_SELF=$ISOLATE_SCRIPT_DIR/isolate.sh

if [[ ${1-} == __minictr_isolated_stage__ ]]; then
    shift
    [[ $# -ge 2 ]] || {
        isolate_error 'internal stage requires ROOTFS and COMMAND'
        exit 2
    }
    rootfs=$1
    shift

    mount_bin=$(isolate_resolve_tool "${MINICTR_MOUNT_BIN:-mount}") || {
        isolate_error 'mount executable is unavailable or unsafe'
        exit 127
    }
    chroot_bin=$(isolate_resolve_tool "${MINICTR_CHROOT_BIN:-chroot}") || {
        isolate_error 'chroot executable is unavailable or unsafe'
        exit 127
    }
    env_bin=$(isolate_resolve_tool "${MINICTR_ENV_BIN:-env}") || {
        isolate_error 'env executable is unavailable or unsafe'
        exit 127
    }

    [[ $rootfs == /* && $rootfs != / && -d $rootfs ]] || {
        isolate_error 'rootfs must be an absolute directory other than /'
        exit 2
    }
    [[ -d $rootfs/proc && ! -L $rootfs/proc ]] || {
        isolate_error 'rootfs must contain a real /proc directory'
        exit 2
    }

    # The namespace begins with a copy of the host mount table.  Make every
    # mount private before adding container mounts so no event can propagate
    # back to the host namespace.
    "$mount_bin" --make-rprivate / 2>/dev/null || {
        isolate_error 'could not make the mount namespace private'
        exit 1
    }
    "$mount_bin" -t proc -o nosuid,noexec,nodev proc "$rootfs/proc" 2>/dev/null || {
        isolate_error 'could not mount the container proc filesystem'
        exit 1
    }

    # Clear the host environment before chroot so credentials and control
    # variables are not inherited by the payload.  PATH is intentionally small
    # and is interpreted only after chroot.
    exec "$env_bin" -i \
        PATH=/usr/sbin:/usr/bin:/sbin:/bin \
        HOME=/root \
        container=minictr \
        "$chroot_bin" "$rootfs" "$@"
    isolate_error 'could not execute chroot'
    exit 126
fi

[[ $# -ge 2 ]] || {
    isolate_error 'usage: isolate.sh ROOTFS COMMAND [ARG...]'
    exit 2
}
rootfs=$1
shift
[[ $rootfs == /* && $rootfs != / && -d $rootfs ]] || {
    isolate_error 'rootfs must be an absolute directory other than /'
    exit 2
}

unshare_bin=$(isolate_resolve_tool "${MINICTR_UNSHARE_BIN:-unshare}") || {
    isolate_error 'unshare executable is unavailable or unsafe'
    exit 127
}

# A new user namespace maps the invoking user to namespace root, permitting the
# mount/chroot operations without host root.  The other namespaces isolate the
# mount table, process IDs, hostname/domain name, IPC, and network stack.  No
# host directory is bind-mounted into the rootfs.
exec "$unshare_bin" \
    --user \
    --map-root-user \
    --mount \
    --pid \
    --uts \
    --ipc \
    --net \
    --fork \
    --kill-child \
    "$ISOLATE_SELF" __minictr_isolated_stage__ "$rootfs" "$@"
isolate_error 'could not execute unshare'
exit 126
