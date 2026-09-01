#!/usr/bin/env bash
set -euo pipefail

here=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo=$(CDPATH= cd -- "$here/.." && pwd -P)
target=${1:-"$repo/starter/minictr"}
iterations=${2:-25}

if [[ ! -x $target ]]; then
    printf 'benchmark: target is not executable: %s\n' "$target" >&2
    exit 2
fi
if [[ ! $iterations =~ ^[0-9]+$ ]] || ((iterations < 1 || iterations > 10000)); then
    printf 'benchmark: ITERATIONS must be an integer from 1 through 10000\n' >&2
    exit 2
fi
target=$(CDPATH= cd -- "$(dirname -- "$target")" && printf '%s/%s\n' "$PWD" "$(basename -- "$target")")
timeout_bin=$(command -v timeout) || {
    printf 'benchmark: the timeout utility is required\n' >&2
    exit 2
}

work=$(mktemp -d "${TMPDIR:-/tmp}/minictr-benchmark.XXXXXX")
cleanup() {
    rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM
export MINICTR_HOME="$work/state"
rootfs="$work/rootfs"
mkdir -p -- "$rootfs" "$MINICTR_HOME"

if [[ -n ${EPOCHREALTIME+x} ]]; then
    clock_source='Bash EPOCHREALTIME (microseconds)'
    date_bin=
else
    date_bin=$(command -v date) || {
        printf 'benchmark: Bash EPOCHREALTIME or GNU date is required\n' >&2
        exit 2
    }
    date_probe=$("$date_bin" +%s%N 2>/dev/null) || date_probe=
    if [[ ! $date_probe =~ ^[0-9]{19}$ ]]; then
        printf 'benchmark: date does not provide a nanosecond clock\n' >&2
        exit 2
    fi
    clock_source='date +%s%N (converted to microseconds)'
fi

now_us() {
    local stamp
    if [[ -n ${EPOCHREALTIME+x} ]]; then
        stamp=${EPOCHREALTIME/./}
        printf '%s\n' "$((10#$stamp))"
    else
        stamp=$("$date_bin" +%s%N) || return 1
        printf '%s\n' "$((10#$stamp / 1000))"
    fi
}

error_log=$work/operation.err
measure() {
    local iteration=$1
    local operation=$2
    shift 2
    local started finished elapsed status
    started=$(now_us)
    set +e
    "$timeout_bin" --signal=TERM --kill-after=2s 15s "$@" \
        >"$work/operation.out" 2>"$error_log"
    status=$?
    set -e
    finished=$(now_us)
    elapsed=$((finished - started))
    printf '%d\t%s\t%d\t%d\n' "$iteration" "$operation" "$elapsed" "$status"
    if ((status != 0)); then
        printf 'benchmark: %s failed in iteration %d with status %d\n' \
            "$operation" "$iteration" "$status" >&2
        sed 's/^/benchmark: command stderr: /' "$error_log" >&2
        return "$status"
    fi
}

printf '# target=%s\n' "$target" >&2
printf '# iterations=%d\n' "$iterations" >&2
printf '# bash=%s\n' "$BASH_VERSION" >&2
printf '# kernel=%s\n' "$(uname -sr)" >&2
printf '# clock=%s\n' "$clock_source" >&2
printf '# per_operation_timeout=15s (+2s forced-termination grace)\n' >&2
printf 'iteration\toperation\tduration_us\tstatus\n'

for ((iteration = 1; iteration <= iterations; iteration += 1)); do
    printf -v name 'bench-%06d' "$iteration"
    measure "$iteration" create "$target" create "$name" "$rootfs"
    measure "$iteration" ps "$target" ps
    measure "$iteration" delete "$target" delete "$name"
done
