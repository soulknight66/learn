#!/usr/bin/env bash
set -u

subject=${1-starter/tinybox.sh}
if [ ! -f "$subject" ]; then
    printf 'not ok - controller does not exist: %s\n' "$subject"
    exit 1
fi

temp_parent=${TMPDIR:-.}
[ -d "$temp_parent" ] && [ -w "$temp_parent" ] || temp_parent=.
suite_root=$(mktemp -d "$temp_parent/tinybox-public.XXXXXX") || exit 1
trap 'rm -rf -- "$suite_root"' EXIT HUP INT TERM
fake_runner=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/fake_runner.sh
tests=0
failures=0
cli_status=0
cli_output=
case_number=0

pass() {
    tests=$((tests + 1))
    printf 'ok %s - %s\n' "$tests" "$1"
}

fail() {
    tests=$((tests + 1))
    failures=$((failures + 1))
    printf 'not ok %s - %s\n' "$tests" "$1"
}

new_case() {
    case_number=$((case_number + 1))
    case_root=$suite_root/case-$case_number
    state_dir=$case_root/state
    rootfs=$case_root/source-rootfs
    error_log=$case_root/stderr
    mkdir -p "$rootfs/etc" "$rootfs/tmp"
    printf 'original\n' >"$rootfs/etc/message"
    export TINYBOX_STATE_DIR=$state_dir
    export TINYBOX_RUNNER=$fake_runner
    unset TINYBOX_FAKE_LOG TINYBOX_FAKE_EXIT
}

run_cli() {
    cli_output=$(bash "$subject" "$@" 2>"$error_log")
    cli_status=$?
}

new_case
run_cli help
if [ "$cli_status" -eq 0 ] && printf '%s\n' "$cli_output" | grep -q 'create NAME ROOTFS'; then
    pass 'help describes the command interface'
else
    fail 'help describes the command interface'
fi

new_case
run_cli create ../escape "$rootfs"
if [ "$cli_status" -ne 0 ] && [ ! -e "$state_dir/escape" ] && [ ! -e "$case_root/escape" ]; then
    pass 'a traversal-shaped name is rejected before path use'
else
    fail 'a traversal-shaped name is rejected before path use'
fi

new_case
run_cli create alpha "$rootfs"
create_status=$cli_status
create_output=$cli_output
printf 'changed\n' >"$rootfs/etc/message"
copied_message=
if [ -f "$state_dir/containers/alpha/rootfs/etc/message" ]; then
    copied_message=$(sed -n '1p' "$state_dir/containers/alpha/rootfs/etc/message")
fi
if [ "$create_status" -eq 0 ] && [ "$create_output" = alpha ] && [ "$copied_message" = original ]; then
    pass 'create publishes an independent rootfs copy'
else
    fail 'create publishes an independent rootfs copy'
fi

run_cli create alpha "$rootfs"
if [ "$create_status" -eq 0 ] && [ "$cli_status" -ne 0 ]; then
    pass 'duplicate create is rejected'
else
    fail 'duplicate create is rejected'
fi

run_cli inspect alpha
expected_inspect=$(printf 'name=alpha\nstatus=CREATED\nexit_code=')
if [ "$cli_status" -eq 0 ] && [ "$cli_output" = "$expected_inspect" ]; then
    pass 'inspect emits deterministic records'
else
    fail 'inspect emits deterministic records'
fi

run_cli create beta "$rootfs"
run_cli list
expected_list=$(printf 'alpha\tCREATED\nbeta\tCREATED')
if [ "$cli_status" -eq 0 ] && [ "$cli_output" = "$expected_list" ]; then
    pass 'list is sorted and machine-readable'
else
    fail 'list is sorted and machine-readable'
fi

export TINYBOX_FAKE_LOG=$case_root/runner.log
export TINYBOX_FAKE_EXIT=7
run_cli run alpha -- /bin/echo 'two words' '*'
run_status=$cli_status
run_output=$cli_output
argv_ok=false
if [ -f "$TINYBOX_FAKE_LOG" ] \
    && grep -Fqx 'argc=5' "$TINYBOX_FAKE_LOG" \
    && grep -Fqx 'arg[2]=/bin/echo' "$TINYBOX_FAKE_LOG" \
    && grep -Fqx 'arg[3]=two words' "$TINYBOX_FAKE_LOG" \
    && grep -Fqx 'arg[4]=*' "$TINYBOX_FAKE_LOG"; then
    argv_ok=true
fi
run_cli inspect alpha
expected_exited=$(printf 'name=alpha\nstatus=EXITED\nexit_code=7')
if [ "$run_status" -eq 7 ] && [ "$run_output" = runner-output ] \
    && [ "$argv_ok" = true ] && [ "$cli_status" -eq 0 ] && [ "$cli_output" = "$expected_exited" ]; then
    pass 'run preserves argv and records the runner exit status'
else
    fail 'run preserves argv and records the runner exit status'
fi

unset TINYBOX_FAKE_LOG TINYBOX_FAKE_EXIT
run_cli delete alpha
delete_status=$cli_status
delete_output=$cli_output
run_cli inspect alpha
if [ "$delete_status" -eq 0 ] && [ "$delete_output" = alpha ] \
    && [ ! -e "$state_dir/containers/alpha" ] && [ "$cli_status" -ne 0 ]; then
    pass 'delete removes exactly an inactive container'
else
    fail 'delete removes exactly an inactive container'
fi

printf '1..%s\n' "$tests"
if [ "$failures" -ne 0 ]; then
    printf '# %s of %s public checks failed\n' "$failures" "$tests"
    exit 1
fi
printf '# all %s public checks passed\n' "$tests"
