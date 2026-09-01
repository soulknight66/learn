#!/usr/bin/env bash
# Test-only entry barrier: do not launch either candidate until both callers exist.

set -u
set -o pipefail

if (( $# < 3 )); then
    printf '%s\n' 'start gate: expected READY_DIR RELEASE_FILE COMMAND [ARG...]' >&2
    exit 64
fi
ready_dir=$1
release_file=$2
shift 2
[[ -d $ready_dir && ! -L $ready_dir ]] || {
    printf '%s\n' 'start gate: READY_DIR must be a real directory' >&2
    exit 64
}
: > "$ready_dir/$BASHPID" || exit 1
for ((attempt = 0; attempt < 400; attempt += 1)); do
    [[ -e $release_file ]] && exec "$@"
    sleep 0.01
done
printf '%s\n' 'start gate: timed out waiting for release' >&2
exit 75
