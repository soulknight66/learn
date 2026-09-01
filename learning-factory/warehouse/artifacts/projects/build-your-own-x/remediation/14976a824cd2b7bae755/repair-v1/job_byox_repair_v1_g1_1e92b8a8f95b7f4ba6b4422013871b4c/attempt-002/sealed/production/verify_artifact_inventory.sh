#!/usr/bin/env bash
# Recompute the inventory and require an exact path-and-digest match.

set -euo pipefail

readonly SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly PACK_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)"
readonly INVENTORY=$PACK_DIR/ARTIFACT_INVENTORY.sha256
readonly BUILDER=$SCRIPT_DIR/build_artifact_inventory.sh

tmp_base=$(CDPATH= cd -- "${TMPDIR:-/tmp}" 2>/dev/null && pwd -P) || {
    printf '%s\n' 'artifact inventory: cannot resolve temporary directory' >&2
    exit 1
}
candidate=$(mktemp "$tmp_base/minictr-inventory.XXXXXX") || exit 1
trap 'rm -f -- "$candidate"' EXIT HUP INT TERM

"$BUILDER" --stdout > "$candidate"
if ! cmp -s -- "$INVENTORY" "$candidate"; then
    printf '%s\n' 'artifact inventory: path or digest set differs from recomputation' >&2
    exit 1
fi
(cd -- "$PACK_DIR" && sha256sum --check --strict ARTIFACT_INVENTORY.sha256 >/dev/null)
entries=$(wc -l < "$INVENTORY")
printf 'artifact inventory: %d entries recomputed and verified\n' "$entries"
