#!/usr/bin/env bash
# Deterministic public contract tests for MiniCTR. No real namespace, mount,
# chroot, sudo, network, or caller-provided rootfs content is used.

set -u
set -o pipefail

TEST_DIR=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P) || exit 70
REPO_DIR=$(CDPATH= cd -- "$TEST_DIR/.." && pwd -P) || exit 70
MINICTR_BIN=${MINICTR_BIN:-$REPO_DIR/starter/minictr}
if [[ $MINICTR_BIN != /* ]]; then
    MINICTR_BIN=$PWD/$MINICTR_BIN
fi
FAKE_ISOLATOR=$TEST_DIR/fakes/isolate_capture.sh
START_GATE=$TEST_DIR/fakes/start_gate.sh

if [[ ! -x $MINICTR_BIN ]]; then
    printf 'public tests: executable not found: %s\n' "$MINICTR_BIN" >&2
    exit 2
fi
if [[ ! -x $FAKE_ISOLATOR ]]; then
    printf 'public tests: fake isolator is not executable: %s\n' "$FAKE_ISOLATOR" >&2
    exit 2
fi
if [[ ! -x $START_GATE ]]; then
    printf 'public tests: start gate is not executable: %s\n' "$START_GATE" >&2
    exit 2
fi
if ! command -v timeout >/dev/null 2>&1; then
    printf '%s\n' 'public tests: required command not found: timeout' >&2
    exit 2
fi

TMP_BASE=$(CDPATH= cd -- "${TMPDIR:-/tmp}" && pwd -P) || {
    printf '%s\n' 'public tests: cannot resolve temporary directory' >&2
    exit 2
}
SUITE_TMP=$(mktemp -d "$TMP_BASE/minictr-public.XXXXXX") || exit 2
readonly TEST_DIR REPO_DIR MINICTR_BIN FAKE_ISOLATOR TMP_BASE SUITE_TMP

declare -a BACKGROUND_PIDS=()

cleanup() {
    local pid
    for pid in "${BACKGROUND_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || :
        fi
        wait "$pid" 2>/dev/null || :
    done
    if [[ -d $SUITE_TMP && $SUITE_TMP == "$TMP_BASE"/minictr-public.* ]]; then
        rm -rf -- "$SUITE_TMP"
    fi
}
trap cleanup EXIT HUP INT TERM

reset_fake_env() {
    unset MINICTR_FAKE_CAPTURE MINICTR_FAKE_STDOUT MINICTR_FAKE_STDERR
    unset MINICTR_FAKE_STATUS MINICTR_FAKE_READY MINICTR_FAKE_RELEASE
    RUN_LC_ALL=
}

LAST_STATUS=0
LAST_STDOUT=
LAST_STDERR=
LAST_BACKGROUND_PID=
RUN_LC_ALL=

run_cli() {
    local state=$1
    local output_prefix=$2
    shift 2

    LAST_STDOUT=$output_prefix.stdout
    LAST_STDERR=$output_prefix.stderr
    local -a locale_env=()
    if [[ -n $RUN_LC_ALL ]]; then
        locale_env=("LC_ALL=$RUN_LC_ALL")
    fi
    env "${locale_env[@]}" MINICTR_HOME="$state" MINICTR_ISOLATOR="$FAKE_ISOLATOR" \
        timeout --preserve-status --signal=TERM --kill-after=1s 5s \
        "$MINICTR_BIN" "$@" >"$LAST_STDOUT" 2>"$LAST_STDERR"
    LAST_STATUS=$?
    return 0
}

snapshot_paths() {
    LC_ALL=C find "$1" -mindepth 1 -printf '%P\t%y\n' | LC_ALL=C sort
}

run_cli_in_background() {
    local state=$1
    local output_prefix=$2
    shift 2

    env MINICTR_HOME="$state" MINICTR_ISOLATOR="$FAKE_ISOLATOR" \
        timeout --preserve-status --signal=TERM --kill-after=1s 8s \
        "$MINICTR_BIN" "$@" >"$output_prefix.stdout" 2>"$output_prefix.stderr" &
    LAST_BACKGROUND_PID=$!
    BACKGROUND_PIDS+=("$LAST_BACKGROUND_PID")
}

fail_case() {
    printf '# %s\n' "$*" >&2
    return 1
}

expect_zero() {
    local context=$1
    (( LAST_STATUS == 0 )) || fail_case "$context: expected status 0, got $LAST_STATUS"
}

expect_nonzero() {
    local context=$1
    (( LAST_STATUS != 0 )) || fail_case "$context: expected nonzero status"
}

expect_silent() {
    local context=$1
    [[ ! -s $LAST_STDOUT && ! -s $LAST_STDERR ]] ||
        fail_case "$context: expected empty stdout and stderr"
}

expect_diagnostic() {
    local context=$1
    local message
    message=$(<"$LAST_STDERR")
    [[ $message == minictr:* ]] || fail_case "$context: stderr must start with 'minictr:'"
}

test_help_and_usage() {
    local case_dir=$SUITE_TMP/help
    local state=$case_dir/state
    mkdir -p -- "$case_dir"
    reset_fake_env

    run_cli "$state" "$case_dir/help" help
    expect_zero help || return
    [[ ! -s $LAST_STDERR ]] || fail_case 'help wrote to stderr' || return
    local help_text
    help_text=$(<"$LAST_STDOUT")
    local word
    for word in create run ps delete; do
        [[ $help_text == *"$word"* ]] || fail_case "help omitted $word" || return
    done
    [[ ! -e $state ]] || fail_case 'help created state' || return

    run_cli "$state" "$case_dir/empty"
    expect_nonzero 'empty invocation' || return
    expect_diagnostic 'empty invocation' || return

    run_cli "$state" "$case_dir/create-arity" create only-a-name
    expect_nonzero 'create missing operand' || return
    expect_diagnostic 'create missing operand' || return

    run_cli "$state" "$case_dir/ps-arity" ps unexpected
    expect_nonzero 'ps extra operand' || return
    expect_diagnostic 'ps extra operand' || return

    run_cli "$state" "$case_dir/help-arity" help unexpected
    expect_nonzero 'help extra operand' || return
    expect_diagnostic 'help extra operand' || return

    run_cli "$state" "$case_dir/unknown" unknown-operation
    expect_nonzero 'unknown operation' || return
    expect_diagnostic 'unknown operation' || return
    [[ ! -e $state ]] || fail_case 'invalid invocation created state' || return
}

test_validation_before_state() {
    local case_dir=$SUITE_TMP/validation
    local state=$case_dir/state
    local rootfs=$case_dir/rootfs
    mkdir -p -- "$rootfs"
    reset_fake_env

    local -a bad_names=(. .. ../escape bad/name -dash 'white space' '')
    local bad_name index=0 locale_name=C available candidate
    local -a available_locales=()
    for bad_name in "${bad_names[@]}"; do
        run_cli "$state" "$case_dir/name-$index" create "$bad_name" "$rootfs"
        expect_nonzero "invalid name $index" || return
        expect_diagnostic "invalid name $index" || return
        [[ ! -e $state ]] || fail_case 'name validation happened after state creation' || return
        (( index += 1 ))
    done

    if command -v locale >/dev/null 2>&1; then
        mapfile -t available_locales < <(locale -a 2>/dev/null)
        for candidate in en_US.utf8 en_US.UTF-8 C.utf8 C.UTF-8; do
            for available in "${available_locales[@]}"; do
                if [[ $available == "$candidate" ]]; then
                    locale_name=$available
                    break 2
                fi
            done
        done
    fi
    RUN_LC_ALL=$locale_name
    run_cli "$state" "$case_dir/non-ascii-name" create 'é' "$rootfs"
    expect_nonzero "non-ASCII name under $locale_name" || return
    expect_diagnostic "non-ASCII name under $locale_name" || return
    [[ ! -e $state ]] || fail_case 'locale-dependent name validation created state' || return
    RUN_LC_ALL=

    local too_long
    printf -v too_long '%065d' 0
    run_cli "$state" "$case_dir/long-name" create "$too_long" "$rootfs"
    expect_nonzero 'overlong name' || return

    run_cli "$state" "$case_dir/relative" create demo relative/rootfs
    expect_nonzero 'relative rootfs' || return
    run_cli "$state" "$case_dir/host-root" create demo /
    expect_nonzero 'host rootfs' || return
    run_cli "$state" "$case_dir/missing" create demo "$case_dir/missing-rootfs"
    expect_nonzero 'missing rootfs' || return
    run_cli "$state" "$case_dir/control" create demo "$case_dir/line"$'\n''break'
    expect_nonzero 'control character in rootfs' || return
    [[ ! -e $state ]] || fail_case 'rootfs validation happened after state creation' || return

    run_cli relative/state "$case_dir/relative-home" ps
    expect_nonzero 'relative MINICTR_HOME' || return
    expect_diagnostic 'relative MINICTR_HOME' || return

    run_cli '' "$case_dir/empty-home" ps
    expect_nonzero 'explicitly empty MINICTR_HOME' || return
    expect_diagnostic 'explicitly empty MINICTR_HOME' || return
}

test_state_rootfs_disjoint() {
    local case_dir=$SUITE_TMP/disjoint
    mkdir -p -- "$case_dir"
    reset_fake_env

    local equal_root=$case_dir/equal before after
    mkdir -p -- "$equal_root"
    : > "$equal_root/sentinel"
    before=$(snapshot_paths "$equal_root") || return
    run_cli "$equal_root" "$case_dir/equal-attempt" create equal "$equal_root"
    expect_nonzero 'state root equal to rootfs' || return
    expect_diagnostic 'state root equal to rootfs' || return
    after=$(snapshot_paths "$equal_root") || return
    [[ -f $equal_root/sentinel && $after == "$before" ]] ||
        fail_case 'equal state/rootfs rejection mutated the rootfs' || return

    local outer_root=$case_dir/outer
    local nested_state=$outer_root/runtime-state
    mkdir -p -- "$outer_root"
    : > "$outer_root/sentinel"
    before=$(snapshot_paths "$outer_root") || return
    run_cli "$nested_state" "$case_dir/nested-attempt" create nested "$outer_root"
    expect_nonzero 'state root nested in rootfs' || return
    expect_diagnostic 'state root nested in rootfs' || return
    after=$(snapshot_paths "$outer_root") || return
    [[ -f $outer_root/sentinel && $after == "$before" ]] ||
        fail_case 'nested state rejection mutated the rootfs' || return

    local parent_state=$case_dir/parent-state
    local inner_root=$parent_state/rootfs
    mkdir -p -- "$inner_root"
    : > "$inner_root/sentinel"
    before=$(snapshot_paths "$parent_state") || return
    run_cli "$parent_state" "$case_dir/ancestor-attempt" create ancestor "$inner_root"
    expect_nonzero 'rootfs nested in state root' || return
    expect_diagnostic 'rootfs nested in state root' || return
    after=$(snapshot_paths "$parent_state") || return
    [[ -f $inner_root/sentinel && $after == "$before" ]] ||
        fail_case 'ancestor state rejection mutated the rootfs or initialized state' || return
}

test_idle_lifecycle() {
    local case_dir=$SUITE_TMP/lifecycle
    local state=$case_dir/state
    local rootfs=$case_dir/'root fs [literal]'
    mkdir -p -- "$rootfs"
    local canonical
    canonical=$(CDPATH= cd -- "$rootfs" && pwd -P) || return 1
    reset_fake_env

    run_cli "$state" "$case_dir/create" create demo "$rootfs"
    expect_zero create || return
    expect_silent create || return

    run_cli "$state" "$case_dir/duplicate" create demo "$rootfs"
    expect_nonzero 'duplicate create' || return
    expect_diagnostic 'duplicate create' || return

    run_cli "$state" "$case_dir/ps-created" ps
    expect_zero 'ps after create' || return
    local expected
    expected=$'NAME\tSTATUS\tPID\tROOTFS\n'"demo"$'\tCREATED\t-\t'"$canonical"
    [[ $(<"$LAST_STDOUT") == "$expected" ]] || fail_case 'ps CREATED row or header differs' || return
    [[ ! -s $LAST_STDERR ]] || fail_case 'ps wrote to stderr' || return

    run_cli "$state" "$case_dir/delete" delete demo
    expect_zero delete || return
    expect_silent delete || return
    [[ -d $rootfs ]] || fail_case 'delete removed the registered rootfs' || return

    run_cli "$state" "$case_dir/ps-empty" ps
    expect_zero 'empty ps' || return
    [[ $(<"$LAST_STDOUT") == $'NAME\tSTATUS\tPID\tROOTFS' ]] ||
        fail_case 'empty ps must contain only the header' || return

    run_cli "$state" "$case_dir/delete-missing" delete demo
    expect_nonzero 'delete missing' || return
    expect_diagnostic 'delete missing' || return
}

test_ps_sorting() {
    local case_dir=$SUITE_TMP/sorting
    local state=$case_dir/state
    local rootfs=$case_dir/rootfs
    mkdir -p -- "$rootfs"
    local canonical
    canonical=$(CDPATH= cd -- "$rootfs" && pwd -P) || return 1
    reset_fake_env

    local name
    for name in zeta middle a10 A2; do
        run_cli "$state" "$case_dir/create-$name" create "$name" "$rootfs"
        expect_zero "create $name" || return
    done
    run_cli "$state" "$case_dir/ps" ps
    expect_zero 'sorted ps' || return
    local expected
    expected=$'NAME\tSTATUS\tPID\tROOTFS\n'
    expected+="A2"$'\tCREATED\t-\t'"$canonical"$'\n'
    expected+="a10"$'\tCREATED\t-\t'"$canonical"$'\n'
    expected+="middle"$'\tCREATED\t-\t'"$canonical"$'\n'
    expected+="zeta"$'\tCREATED\t-\t'"$canonical"
    [[ $(<"$LAST_STDOUT") == "$expected" ]] || fail_case 'ps rows are not C-locale name sorted' || return
}

test_exact_argv() {
    local case_dir=$SUITE_TMP/argv
    local state=$case_dir/state
    local rootfs=$case_dir/'root fs'
    local capture=$case_dir/argv.bin
    local injected=$case_dir/injected
    mkdir -p -- "$rootfs"
    local canonical
    canonical=$(CDPATH= cd -- "$rootfs" && pwd -P) || return 1
    reset_fake_env

    run_cli "$state" "$case_dir/create" create argv-demo "$rootfs"
    expect_zero create || return

    export MINICTR_FAKE_CAPTURE=$capture
    local dangerous
    dangerous="\$(touch -- '$injected')"
    run_cli "$state" "$case_dir/run" run argv-demo literal-command \
        'two words' '*' 'semi;colon' "$dangerous" '' --leading
    expect_zero 'argv run' || return
    [[ ! -e $injected ]] || fail_case 'an argument was evaluated as shell code' || return
    [[ -f $capture ]] || fail_case 'isolator was not invoked' || return

    local -a actual=()
    mapfile -d '' -t actual < "$capture"
    local -a expected=("$canonical" literal-command 'two words' '*' 'semi;colon' "$dangerous" '' --leading)
    (( ${#actual[@]} == ${#expected[@]} )) ||
        fail_case "argv count changed: expected ${#expected[@]}, got ${#actual[@]}" || return
    local index
    for (( index = 0; index < ${#expected[@]}; index++ )); do
        [[ ${actual[index]} == "${expected[index]}" ]] ||
            fail_case "argv element $index changed" || return
    done
}

test_output_status_and_cleanup() {
    local case_dir=$SUITE_TMP/status
    local state=$case_dir/state
    local rootfs=$case_dir/rootfs
    mkdir -p -- "$rootfs"
    reset_fake_env

    run_cli "$state" "$case_dir/create" create status-demo "$rootfs"
    expect_zero create || return

    export MINICTR_FAKE_STDOUT='child stdout'
    export MINICTR_FAKE_STDERR='child stderr'
    export MINICTR_FAKE_STATUS=23
    run_cli "$state" "$case_dir/run" run status-demo false 'unused argument'
    (( LAST_STATUS == 23 )) || fail_case "run changed child status 23 to $LAST_STATUS" || return
    [[ $(<"$LAST_STDOUT") == 'child stdout' ]] || fail_case 'child stdout was changed' || return
    [[ $(<"$LAST_STDERR") == 'child stderr' ]] || fail_case 'child stderr was changed' || return

    reset_fake_env
    run_cli "$state" "$case_dir/ps" ps
    expect_zero 'ps after nonzero child' || return
    local -a rows=()
    mapfile -t rows < "$LAST_STDOUT"
    (( ${#rows[@]} == 2 )) || fail_case 'registration missing after nonzero child' || return
    [[ ${rows[1]} == status-demo$'\tCREATED\t-'$'\t'* ]] ||
        fail_case 'active state remained after nonzero child' || return
}

test_active_run_guards() {
    local case_dir=$SUITE_TMP/active
    local state=$case_dir/state
    local rootfs=$case_dir/rootfs
    local ready=$case_dir/ready
    local release=$case_dir/release
    mkdir -p -- "$rootfs"
    reset_fake_env

    run_cli "$state" "$case_dir/create" create active-demo "$rootfs"
    expect_zero create || return

    export MINICTR_FAKE_READY=$ready
    export MINICTR_FAKE_RELEASE=$release
    run_cli_in_background "$state" "$case_dir/first-run" run active-demo hold
    local run_pid=$LAST_BACKGROUND_PID
    local observed=false
    local attempt
    for (( attempt = 0; attempt < 150; attempt++ )); do
        if [[ -e $ready ]]; then
            observed=true
            break
        fi
        kill -0 "$run_pid" 2>/dev/null || break
        sleep 0.02
    done
    if [[ $observed != true ]]; then
        kill -TERM "$run_pid" 2>/dev/null || :
        wait "$run_pid" 2>/dev/null || :
        fail_case 'first run did not reach the fake isolator'
        return
    fi

    run_cli "$state" "$case_dir/ps-running" ps
    local ps_status=$LAST_STATUS
    local ps_output
    ps_output=$(<"$LAST_STDOUT")

    run_cli "$state" "$case_dir/delete-running" delete active-demo
    local delete_status=$LAST_STATUS

    unset MINICTR_FAKE_READY MINICTR_FAKE_RELEASE
    run_cli "$state" "$case_dir/second-run" run active-demo second
    local second_status=$LAST_STATUS

    : > "$release"
    wait "$run_pid"
    local first_status=$?

    (( ps_status == 0 )) || fail_case 'ps failed during active run' || return
    local running_line=${ps_output#*$'\n'}
    local got_name got_status got_pid got_root
    IFS=$'\t' read -r got_name got_status got_pid got_root <<< "$running_line"
    [[ $got_name == active-demo && $got_status == RUNNING && $got_pid =~ ^[0-9]+$ ]] ||
        fail_case 'ps did not expose a RUNNING row with a numeric host PID' || return
    (( delete_status != 0 )) || fail_case 'delete succeeded during an active run' || return
    (( second_status != 0 )) || fail_case 'a second run succeeded for an active instance' || return
    (( first_status == 0 )) || fail_case "released run returned $first_status" || return

    reset_fake_env
    run_cli "$state" "$case_dir/ps-idle" ps
    expect_zero 'ps after released run' || return
    [[ $(<"$LAST_STDOUT") == *$'\tCREATED\t-'$'\t'* ]] ||
        fail_case 'instance did not return to CREATED' || return
    run_cli "$state" "$case_dir/delete-idle" delete active-demo
    expect_zero 'delete after released run' || return
}

test_concurrent_create_claim() {
    local case_dir=$SUITE_TMP/concurrent
    local state=$case_dir/state
    local rootfs=$case_dir/rootfs
    local ready_dir=$case_dir/ready release_file=$case_dir/release
    mkdir -p -- "$rootfs" "$ready_dir"
    reset_fake_env

    env MINICTR_HOME="$state" MINICTR_ISOLATOR="$FAKE_ISOLATOR" \
        timeout --preserve-status --signal=TERM --kill-after=1s 5s \
        "$START_GATE" "$ready_dir" "$release_file" "$MINICTR_BIN" create race "$rootfs" \
        >"$case_dir/a.stdout" 2>"$case_dir/a.stderr" &
    local pid_a=$!
    BACKGROUND_PIDS+=("$pid_a")
    env MINICTR_HOME="$state" MINICTR_ISOLATOR="$FAKE_ISOLATOR" \
        timeout --preserve-status --signal=TERM --kill-after=1s 5s \
        "$START_GATE" "$ready_dir" "$release_file" "$MINICTR_BIN" create race "$rootfs" \
        >"$case_dir/b.stdout" 2>"$case_dir/b.stderr" &
    local pid_b=$!
    BACKGROUND_PIDS+=("$pid_b")

    local gate_ready=false
    for ((attempt = 0; attempt < 300; attempt += 1)); do
        shopt -s nullglob
        local -a markers=("$ready_dir"/*)
        shopt -u nullglob
        if (( ${#markers[@]} == 2 )); then
            gate_ready=true
            break
        fi
        sleep 0.01
    done
    if [[ $gate_ready != true ]]; then
        fail_case 'both create callers did not reach the synchronized start gate'
        return
    fi
    : > "$release_file"

    wait "$pid_a"
    local status_a=$?
    wait "$pid_b"
    local status_b=$?
    if ! { (( status_a == 0 && status_b != 0 )) || (( status_a != 0 && status_b == 0 )); }; then
        fail_case "concurrent create statuses were $status_a and $status_b; expected one success"
        return
    fi

    run_cli "$state" "$case_dir/ps" ps
    expect_zero 'ps after concurrent create' || return
    local -a rows=()
    mapfile -t rows < "$LAST_STDOUT"
    (( ${#rows[@]} == 2 )) || fail_case 'concurrent create produced other than one registration' || return
    [[ ${rows[1]} == race$'\tCREATED\t-'$'\t'* ]] ||
        fail_case 'concurrent create registration is malformed' || return
}

PASS_COUNT=0
FAIL_COUNT=0
TEST_NUMBER=0

run_case() {
    local label=$1
    local function_name=$2
    (( TEST_NUMBER += 1 ))
    if "$function_name"; then
        printf 'ok %d - %s\n' "$TEST_NUMBER" "$label"
        (( PASS_COUNT += 1 ))
    else
        printf 'not ok %d - %s\n' "$TEST_NUMBER" "$label"
        (( FAIL_COUNT += 1 ))
    fi
}

printf '%s\n' 'TAP version 13' '1..9'
run_case 'help and invalid operation are read-only' test_help_and_usage
run_case 'names, rootfs, and state root are validated' test_validation_before_state
run_case 'state and rootfs trees must be disjoint' test_state_rootfs_disjoint
run_case 'idle create, ps, and delete lifecycle' test_idle_lifecycle
run_case 'ps rows use deterministic C ordering' test_ps_sorting
run_case 'run preserves every argv element' test_exact_argv
run_case 'run preserves streams/status and cleans up' test_output_status_and_cleanup
run_case 'active run blocks delete and a second run' test_active_run_guards
run_case 'synchronized concurrent create has one winner' test_concurrent_create_claim

printf 'public tests: %d passed, %d failed\n' "$PASS_COUNT" "$FAIL_COUNT" >&2
(( FAIL_COUNT == 0 ))
