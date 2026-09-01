#!/usr/bin/env bash
# Deterministic stand-in for the privileged namespace helper.

set -uo pipefail

if [[ -n ${MINICTR_FAKE_REQUIRE_RUNNING:-} ]]; then
    : "${MINICTR_FAKE_CLI:?CLI path is required for running-state assertion}"
    state=$("$MINICTR_FAKE_CLI" ps) || {
        printf 'fake_isolator: ps failed before command work\n' >&2
        exit 120
    }
    expected_name=$MINICTR_FAKE_REQUIRE_RUNNING
    if [[ ! $state =~ $'\n'"$expected_name"$'\tRUNNING\t'[1-9][0-9]*$'\t' ]]; then
        printf 'fake_isolator: instance was not RUNNING before command work\n' >&2
        exit 121
    fi
fi
if [[ -n ${MINICTR_FAKE_ARGV:-} ]]; then
    : > "$MINICTR_FAKE_ARGV"
    for argument in "$@"; do
        printf '%s\0' "$argument" >> "$MINICTR_FAKE_ARGV"
    done
fi
if [[ -n ${MINICTR_FAKE_READY:-} ]]; then
    : > "$MINICTR_FAKE_READY"
fi
if [[ -n ${MINICTR_FAKE_STOPPED_PID:-} ]]; then
    printf '%s\n' "$BASHPID" > "$MINICTR_FAKE_STOPPED_PID"
    kill -STOP "$BASHPID"
fi
if [[ -n ${MINICTR_FAKE_WAIT_FOR:-} ]]; then
    attempts=0
    while [[ ! -f $MINICTR_FAKE_WAIT_FOR ]]; do
        ((attempts += 1))
        if (( attempts >= 500 )); then
            printf 'fake_isolator: timed out waiting for release\n' >&2
            exit 124
        fi
        sleep 0.01
    done
fi
if [[ -n ${MINICTR_FAKE_STDOUT:-} ]]; then
    printf '%s' "$MINICTR_FAKE_STDOUT"
fi
if [[ -n ${MINICTR_FAKE_STDERR:-} ]]; then
    printf '%s' "$MINICTR_FAKE_STDERR" >&2
fi
exit "${MINICTR_FAKE_EXIT:-0}"
