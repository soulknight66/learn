#!/usr/bin/env bash
# Lifecycle and metadata operations for minictr.
#
# Metadata is data, never shell input: this file intentionally contains no
# source/eval path for files below MINICTR_HOME.

minictr_usage() {
    cat <<'EOF'
usage:
  minictr create NAME ROOTFS
  minictr run NAME COMMAND [ARG...]
  minictr ps
  minictr delete NAME
EOF
}

minictr_error() {
    printf 'minictr: %s\n' "$*" >&2
}

minictr_fail() {
    minictr_error "$@"
    return 1
}

minictr_usage_fail() {
    local message=$1
    minictr_error "$message"
    minictr_usage >&2
    return 2
}

minictr_validate_single_line() {
    local value=${1-}
    [[ $value != *$'\n'* && $value != *$'\r'* && $value != *$'\t'* ]]
}

minictr_validate_name() {
    local name=${1-}
    local LC_ALL=C
    [[ $name =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$ ]] || {
        minictr_fail "invalid container name: $name"
        return 1
    }
    [[ $name != . && $name != .. ]] || {
        minictr_fail "invalid container name: $name"
        return 1
    }
}

minictr_select_state_home() {
    if [[ ${MINICTR_HOME+x} == x ]]; then
        MINICTR_REQUESTED_HOME=$MINICTR_HOME
    elif [[ -n ${XDG_STATE_HOME:-} ]]; then
        MINICTR_REQUESTED_HOME=$XDG_STATE_HOME/minictr
    elif [[ -n ${HOME:-} ]]; then
        MINICTR_REQUESTED_HOME=$HOME/.local/state/minictr
    else
        minictr_fail 'MINICTR_HOME, XDG_STATE_HOME, or HOME must be set'
        return 1
    fi

    minictr_validate_single_line "$MINICTR_REQUESTED_HOME" || {
        minictr_fail 'state path contains a tab or line break'
        return 1
    }
    [[ $MINICTR_REQUESTED_HOME == /* && $MINICTR_REQUESTED_HOME != / ]] || {
        minictr_fail 'state path must be an absolute path other than /'
        return 1
    }
}

# Resolve the physical portion of an absolute path without creating its
# nonexistent suffix.  Existing directory symlinks are followed component by
# component; dot components in the prospective suffix are normalized in Bash.
minictr_resolve_prospective_path() {
    local requested=$1 component candidate current=/ remaining

    # Parse with parameter expansion instead of a here-string.  Bash may need
    # temporary storage for a here-string; failure there must never turn a
    # containment check into a successful resolution of "/".
    remaining=${requested#/}
    while :; do
        if [[ $remaining == */* ]]; then
            component=${remaining%%/*}
            remaining=${remaining#*/}
        else
            component=$remaining
            remaining=
        fi
        case $component in
            ''|.)
                continue
                ;;
            ..)
                if [[ $current != / ]]; then
                    current=${current%/*}
                    [[ -n $current ]] || current=/
                fi
                ;;
            *)
                if [[ $current == / ]]; then
                    candidate=/$component
                else
                    candidate=$current/$component
                fi
                if [[ -d $candidate ]]; then
                    current=$(cd -- "$candidate" >/dev/null 2>&1 && pwd -P) || return 1
                else
                    current=$candidate
                fi
                ;;
        esac
        [[ -n $remaining ]] || break
    done
    printf '%s\n' "$current"
}

minictr_require_disjoint_paths() {
    local rootfs=$1 prospective

    minictr_select_state_home || return 1
    prospective=$(minictr_resolve_prospective_path "$MINICTR_REQUESTED_HOME") || {
        minictr_fail 'cannot resolve prospective state directory'
        return 1
    }
    minictr_validate_single_line "$prospective" || {
        minictr_fail 'resolved state path contains a tab or line break'
        return 1
    }
    if [[ $prospective == "$rootfs" || $prospective == "$rootfs/"* ||
          $rootfs == "$prospective/"* ]]; then
        minictr_fail 'state directory and rootfs must be disjoint'
        return 1
    fi
}

minictr_init_state() {
    local requested_home

    umask 077
    minictr_select_state_home || return 1
    requested_home=$MINICTR_REQUESTED_HOME

    mkdir -p -- "$requested_home" 2>/dev/null || {
        minictr_fail "cannot create state directory: $requested_home"
        return 1
    }
    MINICTR_STATE_HOME=$(cd -- "$requested_home" >/dev/null 2>&1 && pwd -P) || {
        minictr_fail "cannot resolve state directory: $requested_home"
        return 1
    }
    minictr_validate_single_line "$MINICTR_STATE_HOME" || {
        minictr_fail 'resolved state path contains a tab or line break'
        return 1
    }
    [[ $MINICTR_STATE_HOME != / ]] || {
        minictr_fail 'resolved state path must not be /'
        return 1
    }

    MINICTR_CONTAINERS=$MINICTR_STATE_HOME/containers
    MINICTR_LOCKS=$MINICTR_STATE_HOME/locks
    mkdir -p -- "$MINICTR_CONTAINERS" "$MINICTR_LOCKS" 2>/dev/null || {
        minictr_fail 'cannot create state subdirectories'
        return 1
    }
    if [[ ! -d $MINICTR_CONTAINERS || -L $MINICTR_CONTAINERS ||
          ! -d $MINICTR_LOCKS || -L $MINICTR_LOCKS ]]; then
        minictr_fail 'state subdirectories must be real directories'
        return 1
    fi
}

minictr_lock() {
    local name=$1
    local lock=$MINICTR_LOCKS/$name.lock
    local attempts=0

    while ! mkdir -- "$lock" 2>/dev/null; do
        ((attempts += 1))
        if (( attempts >= 200 )); then
            minictr_fail "timed out waiting for state lock: $name"
            return 1
        fi
        # A short bounded wait avoids depending on flock while still using the
        # atomicity of mkdir.  Locks are always released by command traps.
        sleep 0.01
    done
    MINICTR_HELD_LOCK=$lock
}

minictr_unlock() {
    if [[ -n ${MINICTR_HELD_LOCK:-} ]]; then
        rmdir -- "$MINICTR_HELD_LOCK" 2>/dev/null || true
        MINICTR_HELD_LOCK=
    fi
}

minictr_container_dir() {
    printf '%s/%s\n' "$MINICTR_CONTAINERS" "$1"
}

minictr_assert_container_dir() {
    local dir=$1
    [[ -d $dir && ! -L $dir ]] || {
        minictr_fail "container does not exist: ${dir##*/}"
        return 1
    }
    [[ -f $dir/rootfs && ! -L $dir/rootfs ]] || {
        minictr_fail "container metadata is invalid: ${dir##*/}"
        return 1
    }
}

minictr_read_rootfs() {
    local dir=$1
    local rootfs
    local -a records=()

    mapfile -t records 2>/dev/null < "$dir/rootfs" || {
        minictr_fail "cannot read container metadata: ${dir##*/}"
        return 1
    }
    # Exactly one record is allowed, including when an extra record is empty.
    [[ ${#records[@]} -eq 1 ]] || {
        minictr_fail "container metadata is invalid: ${dir##*/}"
        return 1
    }
    rootfs=${records[0]}
    [[ $rootfs == /* ]] && minictr_validate_single_line "$rootfs" || {
        minictr_fail "container metadata is invalid: ${dir##*/}"
        return 1
    }
    printf '%s\n' "$rootfs"
}

minictr_atomic_write() {
    local destination=$1
    shift
    local temporary=$destination.tmp.$BASHPID

    # The name is predictable by design so interrupted writes are diagnosable.
    # noclobber makes creation exclusive: a pre-planted regular file or symlink
    # is rejected rather than opened or followed.
    [[ ! -e $temporary && ! -L $temporary ]] || return 1
    ( umask 077; set -o noclobber; printf '%s\n' "$@" > "$temporary" ) \
        2>/dev/null || return 1
    mv -f -- "$temporary" "$destination" 2>/dev/null
}

# Print a zero-based field following the parenthesized comm value in Linux
# /proc/PID/stat.  Parameter expansion avoids temporary-file-dependent shell
# input constructs on this safety path.
minictr_proc_field_after_comm() {
    local pid=$1 wanted=$2 stat rest field index
    local LC_ALL=C

    [[ $pid =~ ^[1-9][0-9]*$ && $wanted =~ ^[0-9]+$ && -r /proc/$pid/stat ]] || return 1
    IFS= read -r stat 2>/dev/null < "/proc/$pid/stat" || return 1
    [[ $stat == *') '* ]] || return 1
    rest=${stat##*) }
    for ((index = 0; index <= wanted; index += 1)); do
        [[ -n $rest ]] || return 1
        field=${rest%% *}
        if (( index == wanted )); then
            printf '%s\n' "$field"
            return 0
        fi
        [[ $rest == *' '* ]] || return 1
        rest=${rest#* }
        while [[ $rest == ' '* ]]; do
            rest=${rest# }
        done
    done
    return 1
}

# Print the Linux process start token for PID.  Pairing this with a PID avoids
# treating an unrelated process as a live container after PID reuse.
minictr_proc_start_token() {
    local token
    local LC_ALL=C
    token=$(minictr_proc_field_after_comm "$1" 19) || return 1
    [[ $token =~ ^[0-9]+$ ]] || return 1
    printf '%s\n' "$token"
}

minictr_proc_state() {
    local state
    local LC_ALL=C
    state=$(minictr_proc_field_after_comm "$1" 0) || return 1
    [[ $state =~ ^[A-Z]$ ]] || return 1
    printf '%s\n' "$state"
}

minictr_child_is_active() {
    local pid=$1 expected=$2 state current
    current=$(minictr_proc_start_token "$pid") || return 1
    [[ $current == "$expected" ]] || return 1
    state=$(minictr_proc_state "$pid") || return 1
    [[ $state != Z && $state != X ]]
}

minictr_forward_signal_to_child() {
    local signal_name=$1 child=${2-} expected=${3-}
    local LC_ALL=C

    if [[ $child =~ ^[1-9][0-9]*$ && $expected =~ ^[0-9]+$ ]] &&
       minictr_child_is_active "$child" "$expected"; then
        kill -"$signal_name" "$child" 2>/dev/null || true
    fi
    return 0
}

minictr_reap_after_signal() {
    local child=$1 expected=$2
    local attempts=0

    # Give the forwarded signal a bounded grace period.  A stopped or
    # uncooperative helper cannot otherwise keep teardown waiting forever.
    while minictr_child_is_active "$child" "$expected"; do
        ((attempts += 1))
        if (( attempts >= 100 )); then
            minictr_forward_signal_to_child KILL "$child" "$expected"
            break
        fi
        sleep 0.01
    done

    # SIGKILL also resumes a stopped task.  Poll for a bounded interval until
    # it is waitable, then reap it before active metadata is removed.
    attempts=0
    while minictr_child_is_active "$child" "$expected"; do
        ((attempts += 1))
        if (( attempts >= 100 )); then
            return 1
        fi
        sleep 0.01
    done
    wait "$child" 2>/dev/null || true
}

minictr_read_live_pid() {
    local dir=$1
    local pid token extra
    local LC_ALL=C

    [[ -f $dir/run && ! -L $dir/run ]] || return 1
    {
        IFS= read -r pid
        IFS= read -r token
        if IFS= read -r extra; then
            return 1
        fi
    } 2>/dev/null < "$dir/run" || return 1
    [[ $pid =~ ^[1-9][0-9]*$ && $token =~ ^[0-9]+$ ]] || return 1
    minictr_child_is_active "$pid" "$token" || return 1
    printf '%s\n' "$pid"
}

minictr_clear_stale_run() {
    local dir=$1
    if [[ -e $dir/run || -L $dir/run ]]; then
        if minictr_read_live_pid "$dir" >/dev/null; then
            return 1
        fi
        [[ -f $dir/run && ! -L $dir/run ]] || {
            minictr_fail "container runtime metadata is invalid: ${dir##*/}"
            return 2
        }
        rm -f -- "$dir/run" 2>/dev/null || {
            minictr_fail "cannot remove stale runtime metadata: ${dir##*/}"
            return 2
        }
    fi
    return 0
}

minictr_create() {
    [[ $# -eq 2 ]] || {
        minictr_usage_fail 'create expects NAME and ROOTFS'
        return
    }
    local name=$1 input_rootfs=$2 rootfs dir temporary

    minictr_validate_name "$name" || return 1
    minictr_validate_single_line "$input_rootfs" || {
        minictr_fail 'rootfs path contains a tab or line break'
        return 1
    }
    [[ $input_rootfs == /* ]] || {
        minictr_fail 'rootfs must be an absolute path'
        return 1
    }
    [[ -d $input_rootfs ]] || {
        minictr_fail "rootfs is not a directory: $input_rootfs"
        return 1
    }
    rootfs=$(cd -- "$input_rootfs" >/dev/null 2>&1 && pwd -P) || {
        minictr_fail "cannot resolve rootfs: $input_rootfs"
        return 1
    }
    minictr_validate_single_line "$rootfs" || {
        minictr_fail 'resolved rootfs path contains a tab or line break'
        return 1
    }
    [[ $rootfs != / ]] || {
        minictr_fail 'refusing to use the host root directory as a rootfs'
        return 1
    }

    minictr_require_disjoint_paths "$rootfs" || return 1
    minictr_init_state || return 1
    dir=$(minictr_container_dir "$name")
    MINICTR_HELD_LOCK=
    minictr_lock "$name" || return 1
    trap 'minictr_unlock' RETURN
    if [[ -e $dir || -L $dir ]]; then
        minictr_fail "container already exists: $name"
        return 1
    fi

    temporary=$MINICTR_CONTAINERS/.create.$name.$BASHPID
    if [[ -e $temporary || -L $temporary ]]; then
        minictr_fail 'temporary state path already exists'
        return 1
    fi
    mkdir -- "$temporary" 2>/dev/null || {
        minictr_fail 'cannot create container metadata'
        return 1
    }
    if ! minictr_atomic_write "$temporary/rootfs" "$rootfs" ||
       ! mv -- "$temporary" "$dir" 2>/dev/null; then
        rm -f -- "$temporary/rootfs" 2>/dev/null || true
        rmdir -- "$temporary" 2>/dev/null || true
        minictr_fail 'cannot commit container metadata'
        return 1
    fi
    minictr_unlock
    trap - RETURN
}

minictr_run_cleanup() {
    local dir=${1-}
    local owner=${2-}
    local expected=${3-}
    local current_pid current_token

    [[ -n $dir ]] || return 0
    MINICTR_HELD_LOCK=
    if ! minictr_lock "${dir##*/}"; then
        return 0
    fi
    if [[ -f $dir/run && ! -L $dir/run ]]; then
        {
            IFS= read -r current_pid || current_pid=
            IFS= read -r current_token || current_token=
        } 2>/dev/null < "$dir/run"
        if [[ $current_pid == "$owner" && $current_token == "$expected" ]]; then
            rm -f -- "$dir/run" 2>/dev/null || true
        fi
    fi
    minictr_unlock
}

minictr_run() {
    [[ $# -ge 2 ]] || {
        minictr_usage_fail 'run expects NAME and COMMAND [ARG...]'
        return
    }
    local name=$1
    shift
    local dir rootfs isolator isolator_dir isolator_leaf child= child_token= owner token status=0 signal=

    minictr_validate_name "$name" || return 1
    [[ -n $1 ]] || {
        minictr_fail 'command must not be empty'
        return 1
    }
    minictr_init_state || return 1
    dir=$(minictr_container_dir "$name")

    MINICTR_HELD_LOCK=
    minictr_lock "$name" || return 1
    minictr_assert_container_dir "$dir" || {
        minictr_unlock
        return 1
    }
    rootfs=$(minictr_read_rootfs "$dir") || {
        minictr_unlock
        return 1
    }
    if [[ ! -d $rootfs || -L $rootfs ]]; then
        minictr_unlock
        minictr_fail "registered rootfs is no longer a real directory: $rootfs"
        return 1
    fi
    if minictr_read_live_pid "$dir" >/dev/null; then
        minictr_unlock
        minictr_fail "container is already running: $name"
        return 1
    fi
    minictr_clear_stale_run "$dir"
    status=$?
    if (( status > 1 )); then
        minictr_unlock
        return 1
    fi

    isolator=${MINICTR_ISOLATOR:-$MINICTR_SCRIPT_DIR/lib/isolate.sh}
    minictr_validate_single_line "$isolator" || {
        minictr_unlock
        minictr_fail 'isolation helper path contains a tab or line break'
        return 1
    }
    if [[ $isolator != /* ]]; then
        isolator_leaf=${isolator##*/}
        if [[ $isolator == */* ]]; then
            isolator_dir=${isolator%/*}
        else
            isolator_dir=.
        fi
        isolator_dir=$(cd -- "$isolator_dir" >/dev/null 2>&1 && pwd -P) || {
            minictr_unlock
            minictr_fail "cannot resolve isolation helper path: $isolator"
            return 1
        }
        isolator=$isolator_dir/$isolator_leaf
    fi
    minictr_validate_single_line "$isolator" || {
        minictr_unlock
        minictr_fail 'resolved isolation helper path contains a tab or line break'
        return 1
    }
    [[ -f $isolator && -x $isolator ]] || {
        minictr_unlock
        minictr_fail "isolation helper is not an executable regular file: $isolator"
        return 1
    }

    # Atomically expose RUNNING before the helper can begin user-command work.
    # The foreground wrapper remains alive until the helper is reaped, so it is
    # also a stable host-visible owner for stale-marker detection.
    owner=$BASHPID
    token=$(minictr_proc_start_token "$owner") || {
        minictr_unlock
        minictr_fail 'cannot identify the foreground wrapper process'
        return 1
    }
    if ! minictr_atomic_write "$dir/run" "$owner" "$token"; then
        minictr_unlock
        minictr_fail 'cannot record running container state'
        return 1
    fi

    trap 'minictr_run_cleanup "$dir" "$owner" "$token"' EXIT
    trap 'signal=TERM; minictr_forward_signal_to_child TERM "$child" "$child_token"' TERM
    trap 'signal=INT; minictr_forward_signal_to_child INT "$child" "$child_token"' INT
    minictr_unlock

    # A signal handled after the active claim but before launch cancels the run
    # without ever starting the helper.
    if [[ -n $signal ]]; then
        trap - TERM INT
        minictr_run_cleanup "$dir" "$owner" "$token"
        trap - EXIT
        [[ $signal == TERM ]] && return 143
        return 130
    fi

    "$isolator" "$rootfs" "$@" &
    child=$!
    child_token=$(minictr_proc_start_token "$child") || {
        wait "$child" 2>/dev/null
        status=$?
        trap - TERM INT
        minictr_run_cleanup "$dir" "$owner" "$token"
        trap - EXIT
        if [[ $signal == TERM ]]; then
            return 143
        elif [[ $signal == INT ]]; then
            return 130
        fi
        return "$status"
    }
    # If a trap ran between fork and token capture it recorded a pending signal
    # without touching the unverified PID.  Forward it now that identity is
    # established.
    if [[ -n $signal ]]; then
        minictr_forward_signal_to_child "$signal" "$child" "$child_token"
    fi
    # Redirect only diagnostics produced by Bash's wait builtin.  The helper
    # inherited the original stderr descriptor when it was launched.
    wait "$child" 2>/dev/null
    status=$?
    if [[ -n $signal ]]; then
        if ! minictr_reap_after_signal "$child" "$child_token"; then
            trap - TERM INT
            # Keep cleanup conservative if even SIGKILL could not make the
            # helper waitable within the bound.
            minictr_error 'isolation helper did not exit after SIGKILL'
            return 1
        fi
    fi
    trap - TERM INT
    minictr_run_cleanup "$dir" "$owner" "$token"
    trap - EXIT

    if [[ $signal == TERM ]]; then
        return 143
    elif [[ $signal == INT ]]; then
        return 130
    fi
    return "$status"
}

minictr_ps() {
    [[ $# -eq 0 ]] || {
        minictr_usage_fail 'ps takes no operands'
        return
    }
    local dir name rootfs pid
    local -a names=()

    minictr_init_state || return 1
    printf 'NAME\tSTATUS\tPID\tROOTFS\n'
    shopt -s nullglob
    for dir in "$MINICTR_CONTAINERS"/*; do
        [[ -d $dir && ! -L $dir ]] || continue
        name=${dir##*/}
        minictr_validate_name "$name" >/dev/null 2>&1 || continue
        names+=("$name")
    done
    shopt -u nullglob
    if (( ${#names[@]} > 0 )); then
        mapfile -t names < <(printf '%s\n' "${names[@]}" | LC_ALL=C sort)
    fi
    for name in "${names[@]}"; do
        dir=$(minictr_container_dir "$name")
        if ! minictr_assert_container_dir "$dir" >/dev/null 2>&1; then
            continue
        fi
        if ! rootfs=$(minictr_read_rootfs "$dir" 2>/dev/null); then
            continue
        fi
        if pid=$(minictr_read_live_pid "$dir"); then
            printf '%s\tRUNNING\t%s\t%s\n' "$name" "$pid" "$rootfs"
        else
            printf '%s\tCREATED\t-\t%s\n' "$name" "$rootfs"
        fi
    done
}

minictr_delete() {
    [[ $# -eq 1 ]] || {
        minictr_usage_fail 'delete expects exactly one NAME'
        return
    }
    local name=$1 dir status

    minictr_validate_name "$name" || return 1
    minictr_init_state || return 1
    dir=$(minictr_container_dir "$name")
    MINICTR_HELD_LOCK=
    minictr_lock "$name" || return 1
    trap 'minictr_unlock' RETURN
    minictr_assert_container_dir "$dir" || return 1
    if minictr_read_live_pid "$dir" >/dev/null; then
        minictr_fail "container is running: $name"
        return 1
    fi
    minictr_clear_stale_run "$dir"
    status=$?
    (( status <= 1 )) || return 1

    # Refuse recursive deletion.  A valid state directory contains exactly the
    # rootfs record (and, after a crash, at most the stale run record above).
    shopt -s nullglob dotglob
    local -a remaining=("$dir"/*)
    shopt -u nullglob dotglob
    if (( ${#remaining[@]} != 1 )) || [[ ${remaining[0]} != "$dir/rootfs" ]]; then
        minictr_fail "container metadata has unexpected files: $name"
        return 1
    fi
    rm -f -- "$dir/rootfs" 2>/dev/null || {
        minictr_fail "cannot remove container metadata: $name"
        return 1
    }
    rmdir -- "$dir" 2>/dev/null || {
        minictr_fail "cannot remove container state directory: $name"
        return 1
    }
    minictr_unlock
    trap - RETURN
}

minictr_main() {
    local command=${1-}
    [[ $# -gt 0 ]] || {
        minictr_usage_fail 'an operation is required'
        return
    }
    shift

    case $command in
        -h|--help|help)
            [[ $# -eq 0 ]] || {
                minictr_usage_fail 'help takes no operands'
                return
            }
            minictr_usage
            return 0
            ;;
        create|run|ps|delete)
            "minictr_$command" "$@"
            ;;
        *)
            minictr_error "unknown command: $command"
            minictr_usage >&2
            return 2
            ;;
    esac
}
