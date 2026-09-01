#!/usr/bin/env bash
# Verify an already transferred learner view without consulting sealed data.

set -euo pipefail

readonly -a EXPECTED_ENTRIES=(
    AGENTS.md
    CONCEPTS.md
    DESIGN_QUESTIONS.md
    MANIFEST.yaml
    README.md
    REQUIREMENTS.md
    environment
    public_tests
    starter
)

verify_error() {
    printf 'learner view verification: %s\n' "$*" >&2
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

if (( $# > 1 )); then
    verify_error 'usage: environment/verify_learner_view.sh [VIEW_DIRECTORY]'
    exit 64
fi
view_arg=${1:-.}
view=$(CDPATH= cd -- "$view_arg" 2>/dev/null && pwd -P) || {
    verify_error 'view is not an accessible directory'
    exit 1
}

mapfile -d '' -t actual_entries < <(
    find "$view" -mindepth 1 -maxdepth 1 -printf '%f\0' | LC_ALL=C sort -z
)
if (( ${#actual_entries[@]} != ${#EXPECTED_ENTRIES[@]} )); then
    verify_error 'top-level entry count differs from the authoritative allowlist'
    exit 1
fi
for ((index = 0; index < ${#EXPECTED_ENTRIES[@]}; index += 1)); do
    if [[ ${actual_entries[index]} != "${EXPECTED_ENTRIES[index]}" ]]; then
        verify_error "unexpected top-level entry: ${actual_entries[index]}"
        exit 1
    fi
done

for entry in README.md AGENTS.md MANIFEST.yaml REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md; do
    if [[ ! -f $view/$entry || -L $view/$entry ]]; then
        verify_error "required learner document is not a regular file: $entry"
        exit 1
    fi
done
for entry in starter public_tests environment; do
    if [[ ! -d $view/$entry || -L $view/$entry ]]; then
        verify_error "required learner directory is not a real directory: $entry"
        exit 1
    fi
done

unsafe=$(find "$view" ! -type d ! -type f -print -quit)
if [[ -n $unsafe ]]; then
    verify_error 'view contains a symbolic link or special file'
    exit 1
fi
while IFS= read -r -d '' candidate; do
    leaf=${candidate##*/}
    if forbidden_leaf "$leaf"; then
        verify_error "view contains a forbidden path component: $leaf"
        exit 1
    fi
done < <(find "$view" -mindepth 1 -print0)

printf '%s\n' 'learner view verification: exact allowlist and recursive exclusions passed'
