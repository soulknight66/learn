#!/usr/bin/env bash
set -uo pipefail

: "${MINICTR_SHIM_ENV_LOG:?log path is required}"
: > "$MINICTR_SHIM_ENV_LOG"
for argument in "$@"; do
    printf '%s\0' "$argument" >> "$MINICTR_SHIM_ENV_LOG"
done
printf '%s' "${MINICTR_SHIM_OUTPUT:-}"
exit "${MINICTR_SHIM_ENV_EXIT:-0}"
