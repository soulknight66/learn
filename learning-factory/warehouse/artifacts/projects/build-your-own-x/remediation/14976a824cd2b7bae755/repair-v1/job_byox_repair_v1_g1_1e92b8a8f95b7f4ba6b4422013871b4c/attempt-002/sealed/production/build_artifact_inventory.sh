#!/usr/bin/env bash
# Generate the deterministic checksum inventory for production pack files.

set -euo pipefail

readonly SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly PACK_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)"
readonly DEFAULT_OUTPUT=$PACK_DIR/ARTIFACT_INVENTORY.sha256
readonly -a ARTIFACT_ROOTS=(
    AGENTS.md
    CONCEPTS.md
    DESIGN_QUESTIONS.md
    LICENSE
    LICENSE_BOUNDARY.md
    MANIFEST.yaml
    PROVENANCE.json
    README.md
    REQUIREMENTS.md
    adversarial
    benchmarks
    debugging
    environment
    public_tests
    review_exercises
    sealed
    starter
)

inventory_error() {
    printf 'artifact inventory: %s\n' "$*" >&2
}

cd -- "$PACK_DIR"
for root in "${ARTIFACT_ROOTS[@]}"; do
    [[ -e $root && ! -L $root ]] || {
        inventory_error "required artifact root is missing or linked: $root"
        exit 1
    }
done
unsafe=$(find "${ARTIFACT_ROOTS[@]}" ! -type d ! -type f -print -quit)
if [[ -n $unsafe ]]; then
    inventory_error 'artifact roots contain a symbolic link or special file'
    exit 1
fi

emit_inventory() {
    while IFS= read -r -d '' path; do
        sha256sum -- "$path"
    done < <(find "${ARTIFACT_ROOTS[@]}" -type f -print0 | LC_ALL=C sort -z)
}

if (( $# > 1 )); then
    inventory_error 'usage: sealed/production/build_artifact_inventory.sh [--stdout]'
    exit 64
fi
if (( $# == 1 )); then
    [[ $1 == --stdout ]] || {
        inventory_error 'the only supported option is --stdout'
        exit 64
    }
    emit_inventory
    exit 0
fi

temporary=$PACK_DIR/.artifact-inventory.tmp.$BASHPID
[[ ! -e $temporary && ! -L $temporary ]] || {
    inventory_error 'private temporary output already exists'
    exit 1
}
trap 'rm -f -- "$temporary" 2>/dev/null || true' EXIT HUP INT TERM
(umask 077; set -o noclobber; emit_inventory > "$temporary")
chmod 644 "$temporary"
mv -f -- "$temporary" "$DEFAULT_OUTPUT"
trap - EXIT HUP INT TERM
printf '%s\n' 'artifact inventory: generated ARTIFACT_INVENTORY.sha256'
