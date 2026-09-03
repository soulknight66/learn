#!/usr/bin/env bash
set -u

repo_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
controller=$repo_root/sealed/reference/tinybox.sh
runner=$repo_root/sealed/reference_tests/controlled_runner.sh
temp_parent=${TMPDIR:-.}
[ -d "$temp_parent" ] && [ -w "$temp_parent" ] || temp_parent=.
test_root=$(mktemp -d "$temp_parent/tinybox-reference.XXXXXX") || exit 1
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM

checks=0
failures=0
command_status=0
command_output=

pass() {
    checks=$((checks + 1))
    printf 'ok %s - %s\n' "$checks" "$1"
}

fail() {
    checks=$((checks + 1))
    failures=$((failures + 1))
    printf 'not ok %s - %s\n' "$checks" "$1"
}

run_controller() {
    command_output=$(bash "$controller" "$@" 2>"$test_root/stderr")
    command_status=$?
}

if bash "$repo_root/public_tests/test_contract.sh" "$controller"; then
    pass 'sealed controller satisfies the public contract'
else
    fail 'sealed controller satisfies the public contract'
fi

export TINYBOX_STATE_DIR=/
export TINYBOX_RUNNER=$runner
run_controller list
if [ "$command_status" -ne 0 ]; then
    pass 'operating-system root is rejected as state'
else
    fail 'operating-system root is rejected as state'
fi

state=$test_root/grammar-state
rootfs=$test_root/grammar-rootfs
mkdir -p "$rootfs/etc" "$rootfs/tmp"
printf 'fixture\n' >"$rootfs/etc/value"
export TINYBOX_STATE_DIR=$state
run_controller create valid "$rootfs"
run_controller run valid /bin/true
missing_separator=$command_status
run_controller run valid -- relative-command
relative_command=$command_status
if [ "$missing_separator" -eq 2 ] && [ "$relative_command" -eq 2 ]; then
    pass 'run requires both the separator and an absolute command'
else
    fail 'run requires both the separator and an absolute command'
fi

printf 'SHELL_CODE=$(id)\n' >"$state/containers/valid/status"
run_controller inspect valid
inspect_bad=$command_status
run_controller list
list_bad=$command_status
if [ "$inspect_bad" -ne 0 ] && [ "$list_bad" -ne 0 ]; then
    pass 'metadata is validated as inert data'
else
    fail 'metadata is validated as inert data'
fi

race_state=$test_root/race-state
export TINYBOX_STATE_DIR=$race_state
bash "$controller" create race "$rootfs" >"$test_root/race-1.out" 2>"$test_root/race-1.err" &
race_pid_1=$!
bash "$controller" create race "$rootfs" >"$test_root/race-2.out" 2>"$test_root/race-2.err" &
race_pid_2=$!
race_result_1=0
race_result_2=0
wait "$race_pid_1" || race_result_1=$?
wait "$race_pid_2" || race_result_2=$?
successes=0
[ "$race_result_1" -eq 0 ] && successes=$((successes + 1))
[ "$race_result_2" -eq 0 ] && successes=$((successes + 1))
if [ "$successes" -eq 1 ] && [ -f "$race_state/containers/race/status" ]; then
    pass 'racing creates publish exactly one complete container'
else
    fail 'racing creates publish exactly one complete container'
fi

active_state=$test_root/active-state
export TINYBOX_STATE_DIR=$active_state
run_controller create active "$rootfs"
export TINYBOX_TEST_STARTED=$test_root/started
export TINYBOX_TEST_RELEASE=$test_root/release
export TINYBOX_TEST_EXIT=19
bash "$controller" run active -- /bin/work >"$test_root/active.out" 2>"$test_root/active.err" &
active_pid=$!
attempts=0
while [ ! -e "$TINYBOX_TEST_STARTED" ] && [ "$attempts" -lt 200 ]; do
    attempts=$((attempts + 1))
    sleep 0.01
done
run_controller inspect active
active_inspect_status=$command_status
active_inspect_output=$command_output
run_controller run active -- /bin/second
second_run_status=$command_status
run_controller delete active
active_delete_status=$command_status
: >"$TINYBOX_TEST_RELEASE"
active_result=0
wait "$active_pid" || active_result=$?
run_controller inspect active
finished_output=$command_output
expected_running=$(printf 'name=active\nstatus=RUNNING\nexit_code=')
expected_finished=$(printf 'name=active\nstatus=EXITED\nexit_code=19')
if [ "$active_inspect_status" -eq 0 ] && [ "$active_inspect_output" = "$expected_running" ] \
    && [ "$second_run_status" -ne 0 ] && [ "$active_delete_status" -ne 0 ] \
    && [ "$active_result" -eq 19 ] && [ "$command_status" -eq 0 ] \
    && [ "$finished_output" = "$expected_finished" ]; then
    pass 'RUNNING state excludes run and delete until completion'
else
    fail 'RUNNING state excludes run and delete until completion'
fi
unset TINYBOX_TEST_STARTED TINYBOX_TEST_RELEASE

contention_state=$test_root/contention-state
export TINYBOX_STATE_DIR=$contention_state
run_controller create contention "$rootfs"
export TINYBOX_TEST_STARTED=$test_root/contention-started
export TINYBOX_TEST_RELEASE=$test_root/contention-runner-release
export TINYBOX_TEST_EXIT=23
bash "$controller" run contention -- /bin/work \
    >"$test_root/contention-run.out" 2>"$test_root/contention-run.err" &
contention_pid=$!
attempts=0
while [ ! -e "$TINYBOX_TEST_STARTED" ] && [ "$attempts" -lt 200 ]; do
    attempts=$((attempts + 1))
    sleep 0.01
done
runner_started=false
[ -e "$TINYBOX_TEST_STARTED" ] && runner_started=true

export TINYBOX_TEST_COMPETITOR_READY=$test_root/contention-competitor-ready
export TINYBOX_TEST_COMPETITOR_RELEASE=$test_root/contention-competitor-release
(
    mapfile() {
        : >"$TINYBOX_TEST_COMPETITOR_READY"
        competitor_attempts=0
        while [ ! -e "$TINYBOX_TEST_COMPETITOR_RELEASE" ] \
            && [ "$competitor_attempts" -lt 200 ]; do
            competitor_attempts=$((competitor_attempts + 1))
            sleep 0.01
        done
        [ -e "$TINYBOX_TEST_COMPETITOR_RELEASE" ] || return 124
        builtin mapfile "$@"
    }
    export -f mapfile
    bash "$controller" delete contention
) >"$test_root/contention-delete.out" 2>"$test_root/contention-delete.err" &
competitor_pid=$!
attempts=0
while [ ! -e "$TINYBOX_TEST_COMPETITOR_READY" ] && [ "$attempts" -lt 200 ]; do
    attempts=$((attempts + 1))
    sleep 0.01
done
competitor_ready=false
[ -e "$TINYBOX_TEST_COMPETITOR_READY" ] && competitor_ready=true

: >"$TINYBOX_TEST_RELEASE"
sleep 0.2
: >"$TINYBOX_TEST_COMPETITOR_RELEASE"
competitor_result=0
wait "$competitor_pid" || competitor_result=$?
contention_result=0
wait "$contention_pid" || contention_result=$?
run_controller inspect contention
expected_contention=$(printf 'name=contention\nstatus=EXITED\nexit_code=23')
if [ "$runner_started" = true ] && [ "$competitor_ready" = true ] \
    && [ "$competitor_result" -eq 3 ] \
    && grep -Fq 'cannot delete container from state RUNNING: contention' \
        "$test_root/contention-delete.err" \
    && [ "$contention_result" -eq 23 ] \
    && [ "$command_status" -eq 0 ] && [ "$command_output" = "$expected_contention" ]; then
    pass 'completion survives a competing mutation holding the name lock'
else
    fail 'completion survives a competing mutation holding the name lock'
fi
unset TINYBOX_TEST_STARTED TINYBOX_TEST_RELEASE TINYBOX_TEST_EXIT
unset TINYBOX_TEST_COMPETITOR_READY TINYBOX_TEST_COMPETITOR_RELEASE

export TINYBOX_STATE_DIR=$active_state
export TINYBOX_TEST_EXIT=255
run_controller run active -- /bin/high-exit
high_result=$command_status
run_controller inspect active
expected_high=$(printf 'name=active\nstatus=EXITED\nexit_code=255')
if [ "$high_result" -eq 255 ] && [ "$command_status" -eq 0 ] \
    && [ "$command_output" = "$expected_high" ]; then
    pass 'runner status 255 is preserved and recorded'
else
    fail 'runner status 255 is preserved and recorded'
fi
unset TINYBOX_TEST_EXIT

signal_state=$test_root/signal-state
export TINYBOX_STATE_DIR=$signal_state
run_controller create signaled "$rootfs"
export TINYBOX_TEST_STARTED=$test_root/signal-started
export TINYBOX_TEST_RELEASE=$test_root/signal-release
bash "$controller" run signaled -- /bin/wait >"$test_root/signal.out" 2>"$test_root/signal.err" &
signal_pid=$!
attempts=0
while [ ! -e "$TINYBOX_TEST_STARTED" ] && [ "$attempts" -lt 200 ]; do
    attempts=$((attempts + 1))
    sleep 0.01
done
kill -TERM "$signal_pid" 2>/dev/null
kill_status=$?
: >"$TINYBOX_TEST_RELEASE"
signal_result=0
wait "$signal_pid" || signal_result=$?
run_controller inspect signaled
expected_signal=$(printf 'name=signaled\nstatus=EXITED\nexit_code=143')
if [ "$kill_status" -eq 0 ] && [ "$signal_result" -eq 143 ] \
    && [ "$command_status" -eq 0 ] && [ "$command_output" = "$expected_signal" ]; then
    pass 'handled TERM records EXITED rather than leaving RUNNING'
else
    fail 'handled TERM records EXITED rather than leaving RUNNING'
fi
unset TINYBOX_TEST_STARTED TINYBOX_TEST_RELEASE

printf '1..%s\n' "$checks"
if [ "$failures" -ne 0 ]; then
    printf '# %s of %s sealed checks failed\n' "$failures" "$checks"
    exit 1
fi
printf '# all %s sealed checks passed\n' "$checks"
