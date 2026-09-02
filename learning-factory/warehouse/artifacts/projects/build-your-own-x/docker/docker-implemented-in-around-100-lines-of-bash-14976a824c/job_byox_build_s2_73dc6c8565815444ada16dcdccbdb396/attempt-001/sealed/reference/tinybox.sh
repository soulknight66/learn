#!/usr/bin/env bash
set -eu

LC_ALL=C
export LC_ALL
umask 077

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
state_dir=
containers_dir=
locks_dir=
tmp_dir=
held_lock=
scratch_dir=
run_active=0
run_name=
loaded_value=

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

die() {
    code=$1
    shift
    printf 'tinybox: %s\n' "$*" >&2
    exit "$code"
}

usage_error() {
    printf 'tinybox: %s\n' "$1" >&2
    usage >&2
    exit 2
}

is_valid_name() {
    [[ ${1-} =~ ^[a-z][a-z0-9_-]{0,31}$ ]]
}

validate_name() {
    is_valid_name "${1-}" || die 3 "invalid container name: ${1-}"
}

ensure_directory() {
    directory=$1
    label=$2
    if [ -L "$directory" ] || { [ -e "$directory" ] && [ ! -d "$directory" ]; }; then
        die 3 "$label is not a safe directory: $directory"
    fi
    mkdir -p -- "$directory" || die 3 "cannot create $label: $directory"
}

init_layout() {
    if [ -n "${TINYBOX_STATE_DIR+x}" ]; then
        state_dir=$TINYBOX_STATE_DIR
    elif [ -n "${XDG_STATE_HOME-}" ]; then
        state_dir=$XDG_STATE_HOME/tinybox
    elif [ -n "${HOME-}" ]; then
        state_dir=$HOME/.local/state/tinybox
    else
        die 3 'no state directory can be determined'
    fi
    case "$state_dir" in
        ''|/) die 3 'state directory must not be empty or /' ;;
    esac
    ensure_directory "$state_dir" 'state directory'
    state_dir=$(CDPATH= cd -- "$state_dir" && pwd -P) \
        || die 3 'cannot resolve state directory'
    [ "$state_dir" != / ] || die 3 'state directory resolves to /'
    containers_dir=$state_dir/containers
    locks_dir=$state_dir/locks
    tmp_dir=$state_dir/tmp
    ensure_directory "$containers_dir" 'containers directory'
    ensure_directory "$locks_dir" 'locks directory'
    ensure_directory "$tmp_dir" 'temporary directory'
}

container_path() {
    validate_name "$1"
    printf '%s/%s\n' "$containers_dir" "$1"
}

require_container() {
    container=$1
    name=$2
    if [ -L "$container" ] || [ ! -d "$container" ]; then
        die 3 "container does not exist: $name"
    fi
}

acquire_lock() {
    name=$1
    [ -z "$held_lock" ] || die 3 'internal error: a lock is already held'
    candidate=$locks_dir/$name.lock
    if ! mkdir -- "$candidate" 2>/dev/null; then
        die 3 "container is busy: $name"
    fi
    held_lock=$candidate
}

release_lock() {
    if [ -n "$held_lock" ]; then
        rmdir -- "$held_lock" 2>/dev/null || true
        held_lock=
    fi
}

cleanup() {
    release_lock
    if [ -n "$scratch_dir" ]; then
        case "$scratch_dir" in
            "$tmp_dir"/*)
                [ "$scratch_dir" != "$tmp_dir" ] && rm -rf -- "$scratch_dir"
                ;;
            *)
                printf 'tinybox: refusing to clean unexpected temporary path: %s\n' \
                    "$scratch_dir" >&2
                ;;
        esac
    fi
}
trap cleanup EXIT

read_one_line() {
    file=$1
    label=$2
    if [ -L "$file" ] || [ ! -f "$file" ]; then
        die 3 "missing or unsafe $label"
    fi
    lines=()
    mapfile -t lines <"$file" || die 3 "cannot read $label"
    [ "${#lines[@]}" -eq 1 ] || die 3 "invalid $label"
    loaded_value=${lines[0]}
}

load_status() {
    container=$1
    read_one_line "$container/status" 'container status'
    case "$loaded_value" in
        CREATED|RUNNING|EXITED) ;;
        *) die 3 "invalid container status: $loaded_value" ;;
    esac
}

atomic_write() {
    destination=$1
    value=$2
    temporary=$destination.tmp.$$
    printf '%s\n' "$value" >"$temporary" \
        || die 3 "cannot write metadata: $destination"
    mv -f -- "$temporary" "$destination" \
        || die 3 "cannot publish metadata: $destination"
}

finish_run() {
    result=$1
    name=$run_name
    container=$(container_path "$name")
    acquire_lock "$name"
    require_container "$container" "$name"
    load_status "$container"
    [ "$loaded_value" = RUNNING ] \
        || die 3 "cannot finish container from state $loaded_value: $name"
    atomic_write "$container/exit_code" "$result"
    atomic_write "$container/status" EXITED
    release_lock
    run_active=0
}

handle_signal() {
    result=$1
    trap - INT TERM
    if [ "$run_active" -eq 1 ]; then
        finish_run "$result"
    fi
    exit "$result"
}
trap 'handle_signal 130' INT
trap 'handle_signal 143' TERM

cmd_create() {
    [ "$#" -eq 2 ] || usage_error 'create requires NAME and ROOTFS'
    name=$1
    source_root=$2
    validate_name "$name"
    [ -d "$source_root" ] || die 3 "rootfs is not a directory: $source_root"
    source_root=$(CDPATH= cd -- "$source_root" && pwd -P) \
        || die 3 "cannot resolve rootfs: $source_root"
    init_layout
    container=$(container_path "$name")
    acquire_lock "$name"
    if [ -e "$container" ] || [ -L "$container" ]; then
        die 3 "container already exists: $name"
    fi
    scratch_dir=$(mktemp -d "$tmp_dir/create.$name.XXXXXX") \
        || die 3 'cannot allocate a temporary container directory'
    mkdir -- "$scratch_dir/rootfs" || die 3 'cannot create rootfs destination'
    cp -a -- "$source_root"/. "$scratch_dir/rootfs"/ \
        || die 3 "cannot copy rootfs: $source_root"
    printf 'CREATED\n' >"$scratch_dir/status" \
        || die 3 'cannot initialize container status'
    mv -T -- "$scratch_dir" "$container" \
        || die 3 "cannot publish container: $name"
    scratch_dir=
    release_lock
    printf '%s\n' "$name"
}

cmd_list() {
    [ "$#" -eq 0 ] || usage_error 'list accepts no operands'
    init_layout
    entries=()
    for container in "$containers_dir"/*; do
        [ -d "$container" ] || continue
        [ ! -L "$container" ] || continue
        name=${container##*/}
        is_valid_name "$name" || continue
        load_status "$container"
        entries+=("$name"$'\t'"$loaded_value")
    done
    if [ "${#entries[@]}" -gt 0 ]; then
        printf '%s\n' "${entries[@]}" | sort
    fi
}

cmd_inspect() {
    [ "$#" -eq 1 ] || usage_error 'inspect requires NAME'
    name=$1
    validate_name "$name"
    init_layout
    container=$(container_path "$name")
    require_container "$container" "$name"
    load_status "$container"
    status=$loaded_value
    exit_code=
    if [ -e "$container/exit_code" ] || [ -L "$container/exit_code" ]; then
        read_one_line "$container/exit_code" 'container exit code'
        [[ $loaded_value =~ ^[0-9]+$ ]] \
            || die 3 "invalid container exit code: $loaded_value"
        [ "$loaded_value" -le 255 ] \
            || die 3 "invalid container exit code: $loaded_value"
        exit_code=$loaded_value
    fi
    printf 'name=%s\nstatus=%s\nexit_code=%s\n' "$name" "$status" "$exit_code"
}

cmd_run() {
    [ "$#" -ge 3 ] || usage_error 'run requires NAME -- COMMAND'
    name=$1
    separator=$2
    validate_name "$name"
    [ "$separator" = -- ] || usage_error 'run requires the -- separator'
    shift 2
    case "$1" in
        /*) ;;
        *) usage_error 'run command must be an absolute path' ;;
    esac
    init_layout
    runner=${TINYBOX_RUNNER-$script_dir/runner.sh}
    if [ -L "$runner" ] || [ ! -f "$runner" ] || [ ! -x "$runner" ]; then
        die 3 "runner is not an executable regular file: $runner"
    fi
    container=$(container_path "$name")
    acquire_lock "$name"
    require_container "$container" "$name"
    load_status "$container"
    case "$loaded_value" in
        CREATED|EXITED) ;;
        *) die 3 "cannot run container from state $loaded_value: $name" ;;
    esac
    if [ -L "$container/rootfs" ] || [ ! -d "$container/rootfs" ]; then
        die 3 "container has an unsafe rootfs: $name"
    fi
    rm -f -- "$container/exit_code" \
        || die 3 "cannot clear old exit status: $name"
    atomic_write "$container/status" RUNNING
    release_lock
    run_name=$name
    run_active=1
    if "$runner" "$container/rootfs" "$name" "$@"; then
        result=0
    else
        result=$?
    fi
    finish_run "$result"
    return "$result"
}

cmd_delete() {
    [ "$#" -eq 1 ] || usage_error 'delete requires NAME'
    name=$1
    validate_name "$name"
    init_layout
    container=$(container_path "$name")
    [ "$container" = "$containers_dir/$name" ] \
        || die 3 'refusing an unexpected deletion target'
    acquire_lock "$name"
    require_container "$container" "$name"
    load_status "$container"
    case "$loaded_value" in
        CREATED|EXITED) ;;
        *) die 3 "cannot delete container from state $loaded_value: $name" ;;
    esac
    rm -rf -- "$container" || die 3 "cannot delete container: $name"
    release_lock
    printf '%s\n' "$name"
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
