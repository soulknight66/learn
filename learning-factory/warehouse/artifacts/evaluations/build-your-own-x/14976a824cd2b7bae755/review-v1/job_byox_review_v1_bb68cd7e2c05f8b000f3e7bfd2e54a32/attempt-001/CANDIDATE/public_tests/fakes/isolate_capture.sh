#!/usr/bin/env bash
# Privilege-free stand-in for starter/lib/isolate.sh. It deliberately does not
# execute COMMAND; it exposes argv, output, status, and pause controls to tests.

set -u
set -o pipefail

if (( $# < 2 )); then
    printf '%s\n' 'fake isolator: expected ROOTFS COMMAND [ARG...]' >&2
    exit 64
fi

rootfs=$1
shift

if [[ -n ${MINICTR_FAKE_CAPTURE:-} ]]; then
    printf '%s\0' "$rootfs" "$@" > "$MINICTR_FAKE_CAPTURE"
fi

if [[ -n ${MINICTR_FAKE_STDOUT+x} ]]; then
    printf '%s\n' "$MINICTR_FAKE_STDOUT"
fi

if [[ -n ${MINICTR_FAKE_STDERR+x} ]]; then
    printf '%s\n' "$MINICTR_FAKE_STDERR" >&2
fi

if [[ -n ${MINICTR_FAKE_READY:-} ]]; then
    : > "$MINICTR_FAKE_READY"
fi

if [[ -n ${MINICTR_FAKE_RELEASE:-} ]]; then
    released=false
    for (( attempt = 0; attempt < 400; attempt++ )); do
        if [[ -e $MINICTR_FAKE_RELEASE ]]; then
            released=true
            break
        fi
        sleep 0.02
    done
    if [[ $released != true ]]; then
        printf '%s\n' 'fake isolator: timed out waiting for release' >&2
        exit 75
    fi
fi

status=${MINICTR_FAKE_STATUS:-0}
if [[ ! $status =~ ^[0-9]+$ ]] || (( status > 255 )); then
    printf '%s\n' 'fake isolator: invalid MINICTR_FAKE_STATUS' >&2
    exit 64
fi
exit "$status"
