#!/usr/bin/env bash
set -uo pipefail

: "${MINICTR_SHIM_MOUNT_LOG:?log path is required}"
printf 'CALL\0' >> "$MINICTR_SHIM_MOUNT_LOG"
for argument in "$@"; do
    printf '%s\0' "$argument" >> "$MINICTR_SHIM_MOUNT_LOG"
done
exit "${MINICTR_SHIM_MOUNT_EXIT:-0}"
