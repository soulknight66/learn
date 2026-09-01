#!/usr/bin/env bash
set -euo pipefail

here=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
candidate=${1:-"$here/broken.sh"}
if [[ ! -x $candidate ]]; then
    printf 'test: candidate is not executable: %s\n' "$candidate" >&2
    exit 2
fi
candidate=$(CDPATH= cd -- "$(dirname -- "$candidate")" && printf '%s/%s\n' "$PWD" "$(basename -- "$candidate")")
timeout_bin=$(command -v timeout) || {
    printf 'test: the timeout utility is required\n' >&2
    exit 2
}
work=$(mktemp -d "${TMPDIR:-/tmp}/status-debug.XXXXXX")
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

set +e
"$timeout_bin" --signal=TERM --kill-after=1s 5s \
    "$candidate" "$work/state" "$here/fixtures/exit-23" \
    >"$work/stdout" 2>"$work/stderr"
status=$?
set -e

if ((status != 23)); then
    printf 'not ok - expected child status 23, got %d\n' "$status" >&2
    exit 1
fi
if [[ $(<"$work/state") != CREATED ]]; then
    printf 'not ok - lifecycle state was not restored\n' >&2
    exit 1
fi
if [[ $(<"$work/stdout") != 'child output' || -s $work/stderr ]]; then
    printf 'not ok - child output was changed\n' >&2
    exit 1
fi
printf 'ok - state was restored and status 23 propagated\n'
