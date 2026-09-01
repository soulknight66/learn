#!/usr/bin/env bash
set -u

if (($# < 2)); then
    printf 'usage: broken.sh STATE_FILE COMMAND [ARG...]\n' >&2
    exit 2
fi
state_file=$1
shift

printf 'RUNNING\n' >"$state_file"
"$@"
# Intentionally broken: this successful write replaces the child status.
printf 'CREATED\n' >"$state_file"

