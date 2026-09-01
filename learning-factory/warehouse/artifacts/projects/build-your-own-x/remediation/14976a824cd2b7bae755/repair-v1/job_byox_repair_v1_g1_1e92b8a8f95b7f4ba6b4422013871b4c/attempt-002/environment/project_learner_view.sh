#!/usr/bin/env bash
# Copy exactly the authoritative learner-visible roots into a new directory.

set -euo pipefail

readonly SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly PACK_DIR="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
readonly ALLOWLIST=$SCRIPT_DIR/learner-view.allowlist
readonly -a EXPECTED_ENTRIES=(
    README.md
    AGENTS.md
    MANIFEST.yaml
    REQUIREMENTS.md
    CONCEPTS.md
    DESIGN_QUESTIONS.md
    starter
    public_tests
    environment
)

projection_error() {
    printf 'learner projection: %s\n' "$*" >&2
}

forbidden_leaf() {
    case $1 in
        .git|.env|.venv|credentials.json|secrets|sealed|reference|reference_tests|hidden_tests|\
        solution|solutions|answers)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

if (( $# != 1 )); then
    projection_error 'usage: environment/project_learner_view.sh NEW_DIRECTORY'
    exit 64
fi

# The machine-readable file and executable policy must agree exactly.  This
# prevents an edited allowlist from silently widening a production transfer.
mapfile -t recorded_entries < "$ALLOWLIST"
if (( ${#recorded_entries[@]} != ${#EXPECTED_ENTRIES[@]} )); then
    projection_error 'allowlist entry count differs from the authoritative policy'
    exit 1
fi
for ((index = 0; index < ${#EXPECTED_ENTRIES[@]}; index += 1)); do
    if [[ ${recorded_entries[index]} != "${EXPECTED_ENTRIES[index]}" ]]; then
        projection_error "allowlist mismatch at entry $((index + 1))"
        exit 1
    fi
done

destination_arg=$1
if [[ $destination_arg == */* ]]; then
    destination_parent_arg=${destination_arg%/*}
    destination_leaf=${destination_arg##*/}
    [[ -n $destination_parent_arg ]] || destination_parent_arg=/
else
    destination_parent_arg=.
    destination_leaf=$destination_arg
fi
if [[ -z $destination_leaf || $destination_leaf == . || $destination_leaf == .. ]]; then
    projection_error 'destination must name a new directory'
    exit 64
fi
destination_parent=$(CDPATH= cd -- "$destination_parent_arg" 2>/dev/null && pwd -P) || {
    projection_error 'destination parent is not an existing accessible directory'
    exit 1
}
destination=$destination_parent/$destination_leaf
if [[ -e $destination || -L $destination ]]; then
    projection_error 'destination already exists'
    exit 1
fi
for selected_directory in starter public_tests environment; do
    if [[ $destination == "$PACK_DIR/$selected_directory/"* ]]; then
        projection_error 'destination must not be nested inside an allowlisted source directory'
        exit 1
    fi
done

# Validate every selected source recursively before creating the destination.
for entry in "${EXPECTED_ENTRIES[@]}"; do
    source_path=$PACK_DIR/$entry
    if [[ ! -e $source_path || -L $source_path ]]; then
        projection_error "allowlisted source is missing or is a link: $entry"
        exit 1
    fi
    unsafe=$(find "$source_path" ! -type d ! -type f -print -quit)
    if [[ -n $unsafe ]]; then
        projection_error "allowlisted source contains a link or special file: $entry"
        exit 1
    fi
    while IFS= read -r -d '' selected_path; do
        selected_leaf=${selected_path##*/}
        if forbidden_leaf "$selected_leaf"; then
            projection_error "forbidden nested path in allowlisted source: $entry"
            exit 1
        fi
    done < <(find "$source_path" -mindepth 1 -print0)
done

umask 077
mkdir -- "$destination"
for entry in "${EXPECTED_ENTRIES[@]}"; do
    cp -Rp -- "$PACK_DIR/$entry" "$destination/"
done

"$destination/environment/verify_learner_view.sh" "$destination"
printf '%s\n' 'learner projection: copied and verified the authoritative view'
