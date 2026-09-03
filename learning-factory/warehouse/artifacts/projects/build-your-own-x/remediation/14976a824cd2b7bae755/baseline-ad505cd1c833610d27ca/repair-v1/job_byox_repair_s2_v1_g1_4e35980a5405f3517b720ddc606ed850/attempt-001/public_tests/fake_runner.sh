#!/usr/bin/env bash
set -eu

if [ "$#" -lt 3 ]; then
    printf 'fake-runner: expected ROOTFS NAME COMMAND [ARG ...]\n' >&2
    exit 2
fi

log_path=${TINYBOX_FAKE_LOG-}
if [ -n "$log_path" ]; then
    {
        printf 'argc=%s\n' "$#"
        index=0
        for argument in "$@"; do
            printf 'arg[%s]=%s\n' "$index" "$argument"
            index=$((index + 1))
        done
    } >"$log_path"
fi

printf 'runner-output\n'
exit_code=${TINYBOX_FAKE_EXIT-0}
case "$exit_code" in
    ''|*[!0-9]*)
        printf 'fake-runner: TINYBOX_FAKE_EXIT must be numeric\n' >&2
        exit 2
        ;;
esac
if [ "$exit_code" -gt 255 ]; then
    printf 'fake-runner: TINYBOX_FAKE_EXIT must be at most 255\n' >&2
    exit 2
fi
exit "$exit_code"
