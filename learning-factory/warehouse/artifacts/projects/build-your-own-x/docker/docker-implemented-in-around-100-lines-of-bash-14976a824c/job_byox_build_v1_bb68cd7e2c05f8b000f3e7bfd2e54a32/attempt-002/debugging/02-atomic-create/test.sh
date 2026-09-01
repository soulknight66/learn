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
work=$(mktemp -d "${TMPDIR:-/tmp}/atomic-debug.XXXXXX")
first_pid=
second_pid=
cleanup() {
    [[ -n $first_pid ]] && kill "$first_pid" 2>/dev/null || true
    [[ -n $second_pid ]] && kill "$second_pid" 2>/dev/null || true
    rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM
mkdir -p -- "$work/state/containers" "$work/ready" "$work/root-a" "$work/root-b"
export DEBUG_READY_DIR="$work/ready"
export DEBUG_RELEASE_FILE="$work/release"

"$timeout_bin" --signal=TERM --kill-after=1s 8s \
    "$candidate" "$work/state" same "$work/root-a" >"$work/one.out" 2>"$work/one.err" &
first_pid=$!
"$timeout_bin" --signal=TERM --kill-after=1s 8s \
    "$candidate" "$work/state" same "$work/root-b" >"$work/two.out" 2>"$work/two.err" &
second_pid=$!

ready=0
for ((attempt = 0; attempt < 500; attempt += 1)); do
    shopt -s nullglob
    markers=("$work/ready"/*)
    shopt -u nullglob
    if ((${#markers[@]} == 2)); then
        ready=1
        break
    fi
    sleep 0.01
done
if ((!ready)); then
    printf 'not ok - creators did not reach the debug gate\n' >&2
    exit 1
fi
: >"$DEBUG_RELEASE_FILE"

set +e
wait "$first_pid"
first_status=$?
first_pid=
wait "$second_pid"
second_status=$?
second_pid=
set -e

successes=0
((first_status == 0)) && ((successes += 1))
((second_status == 0)) && ((successes += 1))
if ((successes != 1)); then
    printf 'not ok - expected one success, got statuses %d and %d\n' \
        "$first_status" "$second_status" >&2
    exit 1
fi
if [[ ! -s $work/state/containers/same/rootfs ]]; then
    printf 'not ok - winner left no complete rootfs record\n' >&2
    exit 1
fi
printf 'ok - exactly one creator claimed the name\n'
