#!/usr/bin/env bash
set -eu

usage() {
    cat <<'EOF'
Usage:
  tinybox.sh create NAME ROOTFS
  tinybox.sh run NAME -- /absolute/program [ARG ...]
  tinybox.sh list
  tinybox.sh inspect NAME
  tinybox.sh delete NAME
  tinybox.sh help
EOF
}

usage_error() {
    printf 'tinybox: %s\n' "$1" >&2
    usage >&2
    exit 2
}

validate_name() {
    # TODO: enforce the exact grammar before using a name in a path.
    case ${1-} in
        '') usage_error 'a container name is required' ;;
    esac
}

not_implemented() {
    printf 'tinybox: %s is not implemented yet\n' "$1" >&2
    exit 70
}

cmd_create() {
    [ "$#" -eq 2 ] || usage_error 'create requires NAME and ROOTFS'
    validate_name "$1"
    # TODO: claim the name, copy into a temporary directory, and publish atomically.
    not_implemented create
}

cmd_list() {
    [ "$#" -eq 0 ] || usage_error 'list accepts no operands'
    # TODO: print only complete containers, sorted by name.
    not_implemented list
}

cmd_inspect() {
    [ "$#" -eq 1 ] || usage_error 'inspect requires NAME'
    validate_name "$1"
    # TODO: validate status data and emit the three required records.
    not_implemented inspect
}

cmd_run() {
    [ "$#" -ge 3 ] || usage_error 'run requires NAME -- COMMAND'
    validate_name "$1"
    [ "$2" = -- ] || usage_error 'run requires the -- separator'
    shift 2
    # TODO: transition to RUNNING, call the runner with "$@", then record completion.
    not_implemented run
}

cmd_delete() {
    [ "$#" -eq 1 ] || usage_error 'delete requires NAME'
    validate_name "$1"
    # TODO: enforce state, prove the target is scoped, and remove it.
    not_implemented delete
}

main() {
    command_name=${1-help}
    if [ "$#" -gt 0 ]; then
        shift
    fi
    case "$command_name" in
        help|-h|--help) usage ;;
        create) cmd_create "$@" ;;
        list) cmd_list "$@" ;;
        inspect) cmd_inspect "$@" ;;
        run) cmd_run "$@" ;;
        delete) cmd_delete "$@" ;;
        *) usage_error "unknown command: $command_name" ;;
    esac
}

main "$@"
