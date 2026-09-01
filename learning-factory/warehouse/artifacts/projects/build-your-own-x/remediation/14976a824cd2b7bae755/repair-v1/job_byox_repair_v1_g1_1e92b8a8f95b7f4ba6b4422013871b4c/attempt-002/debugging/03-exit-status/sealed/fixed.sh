#!/usr/bin/env bash
set -u

if (($# < 2)); then
    printf 'usage: fixed.sh STATE_FILE COMMAND [ARG...]\n' >&2
    exit 2
fi
state_file=$1
shift

printf 'RUNNING\n' >"$state_file" || exit 1
"$@"
child_status=$?
if ! printf 'CREATED\n' >"$state_file"; then
    printf 'fixed: could not restore lifecycle state\n' >&2
    if ((child_status == 0)); then
        exit 1
    fi
fi
exit "$child_status"
