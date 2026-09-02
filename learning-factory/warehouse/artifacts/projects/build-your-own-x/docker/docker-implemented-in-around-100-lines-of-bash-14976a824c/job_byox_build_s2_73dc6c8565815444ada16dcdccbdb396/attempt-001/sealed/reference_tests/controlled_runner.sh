#!/usr/bin/env bash
set -eu

[ "$#" -ge 3 ] || exit 2

if [ -n "${TINYBOX_TEST_STARTED-}" ]; then
    : >"$TINYBOX_TEST_STARTED"
fi
if [ -n "${TINYBOX_TEST_RELEASE-}" ]; then
    attempts=0
    while [ ! -e "$TINYBOX_TEST_RELEASE" ]; do
        attempts=$((attempts + 1))
        if [ "$attempts" -ge 200 ]; then
            printf 'controlled-runner: timed out waiting for release\n' >&2
            exit 124
        fi
        sleep 0.01
    done
fi

exit "${TINYBOX_TEST_EXIT-0}"
