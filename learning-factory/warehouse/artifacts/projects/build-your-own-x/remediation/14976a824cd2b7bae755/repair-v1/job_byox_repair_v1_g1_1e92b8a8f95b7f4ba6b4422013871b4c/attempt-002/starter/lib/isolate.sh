#!/usr/bin/env bash
# Linux isolation layer for MiniCTR.
# Interface: isolate.sh ROOTFS COMMAND [ARG...]

set -u
set -o pipefail

if (( $# < 2 )); then
    printf '%s\n' 'minictr isolator: expected ROOTFS COMMAND [ARG...]' >&2
    exit 64
fi

rootfs=$1
shift
declare -a command_argv=("$@")
: "$rootfs" "${command_argv[@]}"

# TODO: establish every required namespace and filesystem boundary, fail closed
# if any setup step is unavailable, and execute command_argv without re-parsing.
printf '%s\n' 'minictr isolator: TODO: implement Linux isolation' >&2
exit 70
