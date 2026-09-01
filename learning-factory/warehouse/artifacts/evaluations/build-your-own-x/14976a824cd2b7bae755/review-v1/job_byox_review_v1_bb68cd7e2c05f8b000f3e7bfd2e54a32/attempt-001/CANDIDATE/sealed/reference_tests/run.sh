#!/usr/bin/env bash
# Deterministic reference tests.  No root privileges or namespaces are needed.

set -uo pipefail

readonly TEST_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly REFERENCE_DIR="$(cd -- "$TEST_DIR/../reference" && pwd -P)"
readonly CLI=$REFERENCE_DIR/minictr
readonly ISOLATE=$REFERENCE_DIR/lib/isolate.sh
readonly FIXTURES=$TEST_DIR/fixtures

TEST_TMP_BASE=$(cd -- "${TMPDIR:-/tmp}" >/dev/null 2>&1 && pwd -P) || exit 1
readonly TEST_TMP_BASE
TEST_TMP=$(mktemp -d "$TEST_TMP_BASE/minictr-reference-tests.XXXXXX") || exit 1
readonly TEST_TMP
trap 'chmod -R u+rwX -- "$TEST_TMP" 2>/dev/null || true; rm -rf -- "$TEST_TMP"' EXIT

passes=0
failures=0

fail() {
    printf 'assertion failed: %s\n' "$*" >&2
    return 1
}

assert_eq() {
    local expected=$1 actual=$2 label=${3:-values differ}
    [[ $actual == "$expected" ]] || {
        printf 'assertion failed: %s\nexpected: <%s>\n  actual: <%s>\n' \
            "$label" "$expected" "$actual" >&2
        return 1
    }
}

assert_contains() {
    local haystack=$1 needle=$2 label=${3:-missing text}
    [[ $haystack == *"$needle"* ]] || fail "$label: <$needle>"
}

assert_file_absent() {
    [[ ! -e $1 && ! -L $1 ]] || fail "path unexpectedly exists: $1"
}

assert_minictr_error_file() {
    local file=$1 first=
    IFS= read -r first < "$file" || true
    [[ $first == minictr:* ]] || fail "stderr does not start with minictr: <$first>"
}

assert_argv() {
    local file=$1
    shift
    local -a actual=()
    mapfile -d '' -t actual < "$file"
    (( ${#actual[@]} == $# )) || {
        fail "argv length: expected $# got ${#actual[@]}"
        return 1
    }
    local index=0 expected
    for expected in "$@"; do
        assert_eq "$expected" "${actual[$index]}" "argv[$index]" || return 1
        ((index += 1))
    done
}

new_case() {
    local label=$1
    CASE_DIR=$TEST_TMP/$label
    CASE_HOME=$CASE_DIR/state
    CASE_ROOTFS=$CASE_DIR/rootfs
    mkdir -p -- "$CASE_ROOTFS/proc"
}

run_test() {
    local name=$1
    if ( "$name" ); then
        printf 'ok - %s\n' "$name"
        ((passes += 1))
    else
        printf 'not ok - %s\n' "$name"
        ((failures += 1))
    fi
}

test_help_and_usage() {
    new_case usage
    local status output error

    "$CLI" --help >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 0 "$status" 'help status' || return 1
    output=$(<"$CASE_DIR/out")
    error=$(<"$CASE_DIR/err")
    assert_contains "$output" 'minictr create NAME ROOTFS' 'help content' || return 1
    assert_eq '' "$error" 'help stderr' || return 1

    "$CLI" >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 2 "$status" 'empty invocation status' || return 1

    "$CLI" mystery >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    error=$(<"$CASE_DIR/err")
    assert_eq 2 "$status" 'unknown command status' || return 1
    assert_contains "$error" 'minictr: unknown command: mystery' 'unknown command error'
}

test_every_usage_error_has_prefix_and_no_state() {
    new_case usage_prefix
    local status
    local -a cases=(
        ''
        'create sample'
        "create sample $CASE_ROOTFS extra"
        'run sample'
        'ps extra'
        'delete'
        'delete sample extra'
        'help extra'
    )
    local invocation
    local -a words=()
    for invocation in "${cases[@]}"; do
        # These fixed test vectors contain no quoting-sensitive arguments.
        words=()
        read -r -a words <<< "$invocation"
        MINICTR_HOME=$CASE_HOME "$CLI" "${words[@]}" \
            >"$CASE_DIR/out" 2>"$CASE_DIR/err"
        status=$?
        [[ $status -ne 0 ]] || fail "usage error succeeded: $invocation" || return 1
        assert_minictr_error_file "$CASE_DIR/err" || return 1
        assert_file_absent "$CASE_HOME" || return 1
    done
}

test_state_setup_errors_are_controlled() {
    new_case state_errors
    local status first=

    MINICTR_HOME= "$CLI" ps >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'explicit empty state root status' || return 1
    assert_minictr_error_file "$CASE_DIR/err" || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'state path must be an absolute path' || return 1

    MINICTR_HOME=/proc/minictr-reference-audit-$$ "$CLI" ps \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'unwritable state root status' || return 1
    assert_minictr_error_file "$CASE_DIR/err" || return 1
    IFS= read -r first < "$CASE_DIR/err" || true
    [[ $first != mkdir:* ]] || fail "raw mkdir diagnostic escaped: $first"
}

test_create_ps_delete_lifecycle() {
    new_case lifecycle
    local root_with_space=$CASE_DIR/'root fs'
    local output error status expected
    mkdir -p -- "$root_with_space/proc"

    MINICTR_HOME=$CASE_HOME "$CLI" create zed "$CASE_ROOTFS" \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err" || return 1
    assert_eq '' "$(<"$CASE_DIR/out")" 'create stdout' || return 1
    assert_eq '' "$(<"$CASE_DIR/err")" 'create stderr' || return 1
    MINICTR_HOME=$CASE_HOME "$CLI" create alpha "$root_with_space" || return 1

    output=$(MINICTR_HOME=$CASE_HOME "$CLI" ps) || return 1
    expected=$(printf 'NAME\tSTATUS\tPID\tROOTFS\nalpha\tCREATED\t-\t%s\nzed\tCREATED\t-\t%s' \
        "$root_with_space" "$CASE_ROOTFS")
    assert_eq "$expected" "$output" 'sorted ps output' || return 1

    MINICTR_HOME=$CASE_HOME "$CLI" delete alpha \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err" || return 1
    assert_eq '' "$(<"$CASE_DIR/out")" 'delete stdout' || return 1
    assert_eq '' "$(<"$CASE_DIR/err")" 'delete stderr' || return 1
    assert_file_absent "$CASE_HOME/containers/alpha" || return 1

    MINICTR_HOME=$CASE_HOME "$CLI" delete alpha \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    error=$(<"$CASE_DIR/err")
    [[ $status -ne 0 ]] || fail 'missing delete unexpectedly succeeded' || return 1
    assert_contains "$error" 'minictr: container does not exist: alpha' 'missing error'
}

test_input_validation_and_duplicates() {
    new_case validation
    local bad status error
    local -a invalid=('bad/name' '.' '..' '-leading' 'name with space'
        'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')

    for bad in "${invalid[@]}"; do
        MINICTR_HOME=$CASE_HOME "$CLI" create "$bad" "$CASE_ROOTFS" \
            >"$CASE_DIR/out" 2>"$CASE_DIR/err"
        status=$?
        [[ $status -ne 0 ]] || fail "invalid name accepted: $bad" || return 1
        error=$(<"$CASE_DIR/err")
        assert_contains "$error" 'minictr: invalid container name:' 'invalid name prefix' || return 1
    done

    MINICTR_HOME=$CASE_HOME "$CLI" create relative relative/root \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'relative rootfs status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'rootfs must be an absolute path' || return 1

    MINICTR_HOME=$CASE_HOME "$CLI" create hostroot / \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'host root refusal status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'refusing to use the host root' || return 1

    MINICTR_HOME=$CASE_HOME "$CLI" create duplicate "$CASE_ROOTFS" || return 1
    MINICTR_HOME=$CASE_HOME "$CLI" create duplicate "$CASE_ROOTFS" \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'duplicate status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'minictr: container already exists: duplicate'
}

test_canonical_paths_reject_control_characters() {
    new_case canonical_controls
    local target=$CASE_DIR/$'root\tcanonical' link=$CASE_DIR/clean-link
    local state_target=$CASE_DIR/$'state\tcanonical' state_link=$CASE_DIR/clean-state
    local status
    mkdir -p -- "$target/proc" "$state_target"
    ln -s -- "$target" "$link"
    ln -s -- "$state_target" "$state_link"

    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$link" \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'canonical rootfs control status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'resolved rootfs path contains a tab' || return 1
    assert_file_absent "$CASE_HOME" || return 1

    MINICTR_HOME=$state_link "$CLI" ps >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'canonical state control status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'resolved state path contains a tab'
}

test_state_and_rootfs_must_be_disjoint_before_writes() {
    new_case disjoint_paths
    local status nested=$CASE_ROOTFS/state/nested

    MINICTR_HOME=$CASE_ROOTFS "$CLI" create equal "$CASE_ROOTFS" \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'equal state/rootfs status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'state directory and rootfs must be disjoint' || return 1
    assert_file_absent "$CASE_ROOTFS/containers" || return 1
    assert_file_absent "$CASE_ROOTFS/locks" || return 1

    MINICTR_HOME=$nested "$CLI" create nested "$CASE_ROOTFS" \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'nested state/rootfs status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'state directory and rootfs must be disjoint' || return 1
    assert_file_absent "$CASE_ROOTFS/state" || return 1

    local parent_state=$CASE_DIR/parent-state
    mkdir -p -- "$parent_state/rootfs/proc"
    MINICTR_HOME=$parent_state "$CLI" create reverse "$parent_state/rootfs" \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'rootfs nested in state status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'state directory and rootfs must be disjoint' || return 1
    assert_file_absent "$parent_state/containers"
}

test_run_preserves_argv_output_and_status() {
    new_case argv
    local log=$CASE_DIR/argv.bin marker=$CASE_DIR/injected status stdout stderr
    local hostile="\$(touch $marker)"
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1

    MINICTR_HOME=$CASE_HOME \
        MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        MINICTR_FAKE_ARGV=$log \
        MINICTR_FAKE_STDOUT='payload stdout' \
        MINICTR_FAKE_STDERR='payload stderr' \
        MINICTR_FAKE_EXIT=23 \
        "$CLI" run sample /bin/demo 'two words' '*' '' "$hostile" $'line\nbreak' \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    stdout=$(<"$CASE_DIR/out")
    stderr=$(<"$CASE_DIR/err")
    assert_eq 23 "$status" 'payload exit status' || return 1
    assert_eq 'payload stdout' "$stdout" 'payload stdout' || return 1
    assert_eq 'payload stderr' "$stderr" 'payload stderr' || return 1
    assert_file_absent "$marker" || return 1
    assert_argv "$log" "$CASE_ROOTFS" /bin/demo 'two words' '*' '' "$hostile" $'line\nbreak' || return 1

    assert_file_absent "$CASE_HOME/containers/sample/run" || return 1
    assert_contains "$(MINICTR_HOME=$CASE_HOME "$CLI" ps)" $'sample\tCREATED\t-'
}

test_relative_isolator_path_is_one_executable() {
    new_case relative_isolator
    local log=$CASE_DIR/argv.bin status
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1

    (
        cd -- "$TEST_DIR" || exit 1
        MINICTR_HOME=$CASE_HOME \
            MINICTR_ISOLATOR=fixtures/fake_isolator.sh \
            MINICTR_FAKE_ARGV=$log \
            MINICTR_FAKE_EXIT=19 \
            "$CLI" run sample /bin/demo 'relative path'
    ) >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 19 "$status" 'relative isolator payload status' || return 1
    assert_eq '' "$(<"$CASE_DIR/err")" 'relative isolator stderr' || return 1
    assert_argv "$log" "$CASE_ROOTFS" /bin/demo 'relative path'
}

test_isolator_seam_accepts_executable_symlink() {
    new_case symlink_isolator
    local log=$CASE_DIR/argv.bin status
    ln -s -- "$FIXTURES/fake_isolator.sh" "$CASE_DIR/isolate-link"
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1

    (
        cd -- "$CASE_DIR" || exit 1
        MINICTR_HOME=$CASE_HOME \
            MINICTR_ISOLATOR=./isolate-link \
            MINICTR_FAKE_ARGV=$log \
            "$CLI" run sample /bin/demo symlink
    ) >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 0 "$status" 'symlink isolator status' || return 1
    assert_eq '' "$(<"$CASE_DIR/err")" 'symlink isolator stderr' || return 1
    assert_argv "$log" "$CASE_ROOTFS" /bin/demo symlink
}

test_running_state_blocks_conflicting_operations() {
    new_case running
    local ready=$CASE_DIR/ready release=$CASE_DIR/release runner status output
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1

    MINICTR_HOME=$CASE_HOME \
        MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        MINICTR_FAKE_REQUIRE_RUNNING=sample \
        MINICTR_FAKE_CLI=$CLI \
        MINICTR_FAKE_READY=$ready \
        MINICTR_FAKE_WAIT_FOR=$release \
        "$CLI" run sample /bin/hold \
        >"$CASE_DIR/runner.out" 2>"$CASE_DIR/runner.err" &
    runner=$!
    trap 'touch "$release" 2>/dev/null || true; kill -TERM "$runner" 2>/dev/null || true; wait "$runner" 2>/dev/null || true' EXIT

    local attempts=0
    while [[ ! -f $ready ]]; do
        ((attempts += 1))
        if (( attempts >= 300 )); then
            fail 'fake isolator did not become ready'
            return 1
        fi
        sleep 0.01
    done

    output=$(MINICTR_HOME=$CASE_HOME "$CLI" ps) || return 1
    [[ $output =~ $'sample\tRUNNING\t'[1-9][0-9]*$'\t'"$CASE_ROOTFS" ]] || {
        fail "ps did not report verified RUNNING state: $output"
        return 1
    }

    MINICTR_HOME=$CASE_HOME "$CLI" delete sample \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'delete running status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'minictr: container is running: sample' || return 1

    MINICTR_HOME=$CASE_HOME MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        "$CLI" run sample /bin/second >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'second run status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'minictr: container is already running: sample' || return 1

    touch "$release"
    wait "$runner"
    status=$?
    assert_eq 0 "$status" 'held run status' || return 1
    trap - EXIT
    output=$(MINICTR_HOME=$CASE_HOME "$CLI" ps) || return 1
    assert_contains "$output" $'sample\tCREATED\t-\t' || return 1
    MINICTR_HOME=$CASE_HOME "$CLI" delete sample
}

test_run_rechecks_registered_rootfs() {
    new_case missing_rootfs
    local log=$CASE_DIR/argv.bin status
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1
    rmdir -- "$CASE_ROOTFS/proc" "$CASE_ROOTFS"

    MINICTR_HOME=$CASE_HOME \
        MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        MINICTR_FAKE_ARGV=$log \
        "$CLI" run sample /bin/noop >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'missing registered rootfs status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'registered rootfs is no longer a real directory' || return 1
    assert_file_absent "$log"
}

test_atomic_write_rejects_planted_symlink() {
    new_case exclusive_temp
    local lock victim temporary log=$CASE_DIR/argv.bin runner status attempts=0
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1
    lock=$CASE_HOME/locks/sample.lock
    victim=$CASE_DIR/outside-victim
    printf '%s\n' 'unchanged victim' > "$victim"
    mkdir -- "$lock"

    MINICTR_HOME=$CASE_HOME \
        MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        MINICTR_FAKE_ARGV=$log \
        "$CLI" run sample /bin/noop >"$CASE_DIR/out" 2>"$CASE_DIR/err" &
    runner=$!
    trap 'rmdir -- "$lock" 2>/dev/null || true; kill -KILL "$runner" 2>/dev/null || true; wait "$runner" 2>/dev/null || true' EXIT
    temporary=$CASE_HOME/containers/sample/run.tmp.$runner
    ln -s -- "$victim" "$temporary"
    rmdir -- "$lock"

    while kill -0 "$runner" 2>/dev/null; do
        ((attempts += 1))
        if (( attempts >= 400 )); then
            fail 'run did not fail after exclusive-create collision'
            return 1
        fi
        sleep 0.01
    done
    wait "$runner" 2>/dev/null
    status=$?
    trap - EXIT
    assert_eq 1 "$status" 'planted temp symlink status' || return 1
    assert_eq 'unchanged victim' "$(<"$victim")" 'outside victim content' || return 1
    [[ -L $temporary ]] || fail 'planted symlink was unexpectedly replaced' || return 1
    assert_file_absent "$log" || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'cannot record running container state' || return 1
    rm -f -- "$temporary"
}

test_signal_teardown_kills_stopped_helper() {
    new_case signal_teardown
    local pid_file=$CASE_DIR/helper.pid runner helper status attempts=0 output
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1

    MINICTR_HOME=$CASE_HOME \
        MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        MINICTR_FAKE_STOPPED_PID=$pid_file \
        "$CLI" run sample /bin/stopped >"$CASE_DIR/out" 2>"$CASE_DIR/err" &
    runner=$!
    trap 'kill -KILL "$runner" "${helper:-}" 2>/dev/null || true; wait "$runner" 2>/dev/null || true' EXIT
    while [[ ! -s $pid_file ]]; do
        ((attempts += 1))
        if (( attempts >= 300 )); then
            fail 'stopped helper did not publish its PID'
            return 1
        fi
        sleep 0.01
    done
    IFS= read -r helper < "$pid_file"
    kill -TERM "$runner"

    attempts=0
    while kill -0 "$runner" 2>/dev/null; do
        ((attempts += 1))
        if (( attempts >= 400 )); then
            fail 'wrapper signal cleanup exceeded its bound'
            return 1
        fi
        sleep 0.01
    done
    wait "$runner" 2>/dev/null
    status=$?
    trap - EXIT
    assert_eq 143 "$status" 'terminated wrapper status' || return 1
    if kill -0 "$helper" 2>/dev/null; then
        fail "stopped helper remains alive: $helper"
        return 1
    fi
    assert_eq '' "$(<"$CASE_DIR/err")" 'wrapper signal stderr' || return 1
    output=$(MINICTR_HOME=$CASE_HOME "$CLI" ps) || return 1
    assert_contains "$output" $'sample\tCREATED\t-\t'
}

test_stale_pid_and_unexpected_files_are_safe() {
    new_case stale
    local state_dir status token
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1
    state_dir=$CASE_HOME/containers/sample
    token=0
    printf '%s\n%s\n' "$$" "$token" > "$state_dir/run"

    # A mismatched start token is stale even if the numeric PID currently exists.
    MINICTR_HOME=$CASE_HOME \
        MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        MINICTR_FAKE_EXIT=42 \
        "$CLI" run sample /bin/noop \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 42 "$status" 'deterministic failing fake status' || return 1
    assert_file_absent "$state_dir/run" || return 1

    : > "$state_dir/unexpected"
    MINICTR_HOME=$CASE_HOME "$CLI" delete sample \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'unexpected metadata delete status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'metadata has unexpected files' || return 1
    [[ -d $state_dir ]] || fail 'safe delete removed a corrupt state directory'
}

test_metadata_is_never_evaluated() {
    new_case metadata
    local marker=$CASE_DIR/evaluated state_file status malicious
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1
    state_file=$CASE_HOME/containers/sample/rootfs
    malicious="\$(touch $marker)"
    printf '%s\n' "$malicious" > "$state_file"

    MINICTR_HOME=$CASE_HOME MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        "$CLI" run sample /bin/noop >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'malformed metadata status' || return 1
    assert_file_absent "$marker" || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'container metadata is invalid'
}

test_metadata_requires_exactly_one_record() {
    new_case metadata_records
    local state_file status
    MINICTR_HOME=$CASE_HOME "$CLI" create sample "$CASE_ROOTFS" || return 1
    state_file=$CASE_HOME/containers/sample/rootfs
    printf '%s\n\n' "$CASE_ROOTFS" > "$state_file"

    MINICTR_HOME=$CASE_HOME MINICTR_ISOLATOR=$FIXTURES/fake_isolator.sh \
        "$CLI" run sample /bin/noop >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    assert_eq 1 "$status" 'extra metadata record status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'container metadata is invalid'
}

test_namespace_helper_uses_safe_argv() {
    new_case isolate
    local unshare_log=$CASE_DIR/unshare.bin mount_log=$CASE_DIR/mount.bin
    local env_log=$CASE_DIR/env.bin status output
    : > "$mount_log"

    MINICTR_UNSHARE_BIN=$FIXTURES/fake_unshare.sh \
        MINICTR_MOUNT_BIN=$FIXTURES/fake_mount.sh \
        MINICTR_CHROOT_BIN=$FIXTURES/fake_chroot.sh \
        MINICTR_ENV_BIN=$FIXTURES/fake_env.sh \
        MINICTR_SHIM_UNSHARE_LOG=$unshare_log \
        MINICTR_SHIM_MOUNT_LOG=$mount_log \
        MINICTR_SHIM_ENV_LOG=$env_log \
        MINICTR_SHIM_OUTPUT='isolated output' \
        MINICTR_SHIM_ENV_EXIT=27 \
        "$ISOLATE" "$CASE_ROOTFS" /bin/demo 'two words' '*' \
        >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    status=$?
    output=$(<"$CASE_DIR/out")
    assert_eq 27 "$status" 'isolation payload status' || return 1
    assert_eq 'isolated output' "$output" 'isolation payload output' || return 1
    assert_eq '' "$(<"$CASE_DIR/err")" 'isolation helper stderr' || return 1

    assert_argv "$unshare_log" \
        --user --map-root-user --mount --pid --uts --ipc --net --fork --kill-child \
        "$ISOLATE" __minictr_isolated_stage__ "$CASE_ROOTFS" /bin/demo 'two words' '*' || return 1
    assert_argv "$mount_log" \
        CALL --make-rprivate / \
        CALL -t proc -o nosuid,noexec,nodev proc "$CASE_ROOTFS/proc" || return 1
    assert_argv "$env_log" \
        -i PATH=/usr/sbin:/usr/bin:/sbin:/bin HOME=/root container=minictr \
        "$FIXTURES/fake_chroot.sh" "$CASE_ROOTFS" /bin/demo 'two words' '*'
}

test_namespace_helper_rejects_missing_proc() {
    new_case missing_proc
    rmdir -- "$CASE_ROOTFS/proc"
    MINICTR_UNSHARE_BIN=$FIXTURES/fake_unshare.sh \
        MINICTR_MOUNT_BIN=$FIXTURES/fake_mount.sh \
        MINICTR_CHROOT_BIN=$FIXTURES/fake_chroot.sh \
        MINICTR_ENV_BIN=$FIXTURES/fake_env.sh \
        MINICTR_SHIM_UNSHARE_LOG=$CASE_DIR/unshare.bin \
        MINICTR_SHIM_MOUNT_LOG=$CASE_DIR/mount.bin \
        MINICTR_SHIM_ENV_LOG=$CASE_DIR/env.bin \
        "$ISOLATE" "$CASE_ROOTFS" /bin/demo >"$CASE_DIR/out" 2>"$CASE_DIR/err"
    local status=$?
    assert_eq 2 "$status" 'missing proc status' || return 1
    assert_contains "$(<"$CASE_DIR/err")" 'rootfs must contain a real /proc directory'
}

run_test test_help_and_usage
run_test test_every_usage_error_has_prefix_and_no_state
run_test test_state_setup_errors_are_controlled
run_test test_create_ps_delete_lifecycle
run_test test_input_validation_and_duplicates
run_test test_canonical_paths_reject_control_characters
run_test test_state_and_rootfs_must_be_disjoint_before_writes
run_test test_run_preserves_argv_output_and_status
run_test test_relative_isolator_path_is_one_executable
run_test test_isolator_seam_accepts_executable_symlink
run_test test_running_state_blocks_conflicting_operations
run_test test_run_rechecks_registered_rootfs
run_test test_atomic_write_rejects_planted_symlink
run_test test_signal_teardown_kills_stopped_helper
run_test test_stale_pid_and_unexpected_files_are_safe
run_test test_metadata_is_never_evaluated
run_test test_metadata_requires_exactly_one_record
run_test test_namespace_helper_uses_safe_argv
run_test test_namespace_helper_rejects_missing_proc

printf '%s passed; %s failed\n' "$passes" "$failures"
(( failures == 0 ))
