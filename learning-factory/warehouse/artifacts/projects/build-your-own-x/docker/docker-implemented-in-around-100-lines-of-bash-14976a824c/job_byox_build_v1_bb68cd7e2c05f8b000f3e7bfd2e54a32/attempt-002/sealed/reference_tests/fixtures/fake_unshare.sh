#!/usr/bin/env bash
set -uo pipefail

: "${MINICTR_SHIM_UNSHARE_LOG:?log path is required}"
: > "$MINICTR_SHIM_UNSHARE_LOG"
for argument in "$@"; do
    printf '%s\0' "$argument" >> "$MINICTR_SHIM_UNSHARE_LOG"
done
while [[ ${1-} == --* ]]; do
    shift
done
exec "$@"
