#!/usr/bin/env bash
# Capability inventory. This script creates and removes one private empty
# directory to prove temporary storage; it never creates MiniCTR state, enters
# a namespace, mounts, changes root, or contacts a network service.

set -u
set -o pipefail

mode=public
if (( $# > 1 )); then
    printf '%s\n' 'usage: environment/check.sh [--require-isolation-tools]' >&2
    exit 64
fi
if (( $# == 1 )); then
    case $1 in
        --require-isolation-tools) mode=isolation ;;
        -h|--help)
            printf '%s\n' 'usage: environment/check.sh [--require-isolation-tools]'
            exit 0
            ;;
        *)
            printf 'environment check: unknown option: %s\n' "$1" >&2
            exit 64
            ;;
    esac
fi

missing_required=0

check_command() {
    local classification=$1
    local command_name=$2
    if command -v "$command_name" >/dev/null 2>&1; then
        printf '%s\t%s\t%s\n' "$classification" "$command_name" available
    else
        printf '%s\t%s\t%s\n' "$classification" "$command_name" missing
        if [[ $classification == required ]]; then
            missing_required=1
        fi
    fi
}

printf '%s\t%s\t%s\n' CLASS COMMAND STATUS
for command_name in bash cp env find mkdir mktemp rm rmdir sort timeout; do
    check_command required "$command_name"
done

check_temporary_storage() {
    local requested=${TMPDIR:-/tmp} resolved probe

    resolved=$(CDPATH= cd -- "$requested" 2>/dev/null && pwd -P) || {
        printf '%s\t%s\t%s\n' required temporary-storage missing
        printf 'environment check: cannot resolve temporary directory: %s\n' "$requested" >&2
        missing_required=1
        return 0
    }
    probe=$(umask 077; mktemp -d "$resolved/minictr-environment-check.XXXXXX" 2>/dev/null) || {
        printf '%s\t%s\t%s\n' required temporary-storage unusable
        printf 'environment check: cannot create a private temporary directory below: %s\n' \
            "$resolved" >&2
        missing_required=1
        return 0
    }
    if [[ ! -d $probe || -L $probe ]] || ! rmdir -- "$probe" 2>/dev/null; then
        printf '%s\t%s\t%s\n' required temporary-storage unsafe
        printf '%s\n' 'environment check: temporary-directory probe was not a removable real directory' >&2
        missing_required=1
        return 0
    fi
    printf '%s\t%s\t%s\n' required temporary-storage available
}

check_temporary_storage

isolation_class=optional
if [[ $mode == isolation ]]; then
    isolation_class=required
fi
for command_name in unshare chroot mount; do
    check_command "$isolation_class" "$command_name"
done
for command_name in findmnt nsenter shellcheck bats busybox; do
    check_command optional "$command_name"
done

if [[ $(uname -s 2>/dev/null || :) == Linux ]]; then
    printf '%s\t%s\t%s\n' info kernel Linux
else
    printf '%s\t%s\t%s\n' info kernel non-Linux
    if [[ $mode == isolation ]]; then
        missing_required=1
    fi
fi

if (( BASH_VERSINFO[0] >= 4 )); then
    printf '%s\t%s\t%s\n' info bash-version "${BASH_VERSION}"
else
    printf '%s\t%s\t%s\n' required bash-version 'Bash 4+ required'
    missing_required=1
fi

if (( missing_required != 0 )); then
    printf '%s\n' 'environment check: required capabilities are missing' >&2
    exit 1
fi

if [[ $mode == isolation ]]; then
    printf '%s\n' 'environment check: tools found; kernel permission remains unverified' >&2
else
    printf '%s\n' 'environment check: public-test prerequisites found' >&2
fi
