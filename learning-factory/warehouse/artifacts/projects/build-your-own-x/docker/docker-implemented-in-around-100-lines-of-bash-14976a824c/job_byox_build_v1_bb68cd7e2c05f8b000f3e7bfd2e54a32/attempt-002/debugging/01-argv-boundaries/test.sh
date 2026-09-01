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
work=$(mktemp -d "${TMPDIR:-/tmp}/argv-debug.XXXXXX")
trap 'rm -rf -- "$work"' EXIT HUP INT TERM
mkdir -- "$work/glob-one" "$work/glob-two"

set +e
actual=$(cd -- "$work" && "$timeout_bin" --signal=TERM --kill-after=1s 5s "$candidate" \
    "$here/fixtures/record-argv" '/root fs' 'program name' \
    'two words' '*' '')
status=$?
set -e

expected=$(printf '%s\n' \
    '</root fs>' \
    '<program name>' \
    '<two words>' \
    '<*>' \
    '<>')

if ((status != 0)); then
    printf 'not ok - wrapper returned %d\n' "$status" >&2
    exit 1
fi
if [[ $actual != "$expected" ]]; then
    printf 'not ok - argv boundaries changed\nexpected:\n%s\nactual:\n%s\n' \
        "$expected" "$actual" >&2
    exit 1
fi
printf 'ok - exact argv boundaries were retained\n'
