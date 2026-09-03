#!/usr/bin/env bash
set -u

repo_root=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
controller=$repo_root/sealed/reference/tinybox.sh
exact_runner=$repo_root/sealed/reference_tests/exact_argv_runner.sh
temp_parent=${TMPDIR:-.}
[ -d "$temp_parent" ] && [ -w "$temp_parent" ] || temp_parent=.
test_root=$(mktemp -d "$temp_parent/tinybox-adversarial.XXXXXX") || exit 1
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM

checks=0
failures=0
command_status=0

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
    bash "$controller" "$@" >"$test_root/stdout" 2>"$test_root/stderr"
    command_status=$?
}

rootfs=$test_root/rootfs
mkdir -p "$rootfs/etc" "$rootfs/tmp"
printf 'fixture\n' >"$rootfs/etc/value"
export TINYBOX_RUNNER=$exact_runner

outside=$test_root/outside-layout
state=$test_root/symlink-layout-state
mkdir -p "$outside" "$state"
printf 'preserve-me\n' >"$outside/sentinel"
ln -s "$outside" "$state/containers"
export TINYBOX_STATE_DIR=$state
run_controller list
sentinel=$(sed -n '1p' "$outside/sentinel")
if [ "$command_status" -ne 0 ] && [ "$sentinel" = preserve-me ]; then
    pass 'a symlinked state-layout directory is rejected'
else
    fail 'a symlinked state-layout directory is rejected'
fi

state=$test_root/container-link-state
export TINYBOX_STATE_DIR=$state
run_controller list
outside_container=$test_root/outside-container
mkdir -p "$outside_container"
printf 'CREATED\n' >"$outside_container/status"
printf 'outside\n' >"$outside_container/sentinel"
ln -s "$outside_container" "$state/containers/victim"
run_controller delete victim
sentinel=$(sed -n '1p' "$outside_container/sentinel")
if [ "$command_status" -ne 0 ] && [ "$sentinel" = outside ]; then
    pass 'a symlinked container cannot redirect deletion'
else
    fail 'a symlinked container cannot redirect deletion'
fi

state=$test_root/metadata-link-state
export TINYBOX_STATE_DIR=$state
run_controller create metadata "$rootfs"
rm -f -- "$state/containers/metadata/status"
printf 'CREATED\n' >"$test_root/external-status"
ln -s "$test_root/external-status" "$state/containers/metadata/status"
run_controller inspect metadata
if [ "$command_status" -ne 0 ]; then
    pass 'symlinked metadata is rejected'
else
    fail 'symlinked metadata is rejected'
fi

state=$test_root/name-state
export TINYBOX_STATE_DIR=$state
bad_names=('' '../escape' '/absolute' 'Upper' 'two words' 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
all_rejected=true
for bad_name in "${bad_names[@]}"; do
    run_controller create "$bad_name" "$rootfs"
    [ "$command_status" -ne 0 ] || all_rejected=false
done
if [ "$all_rejected" = true ] && [ ! -e "$state/escape" ]; then
    pass 'invalid name classes are rejected without publication'
else
    fail 'invalid name classes are rejected without publication'
fi

state=$test_root/'state with spaces'
export TINYBOX_STATE_DIR=$state
run_controller create argvcase "$rootfs"
create_status=$command_status
run_controller run argvcase -- /bin/tool 'two words' '*' 'semi;colon' ''
run_status=$command_status
run_controller inspect argvcase
inspect_output=$(sed -n '1,3p' "$test_root/stdout")
expected=$(printf 'name=argvcase\nstatus=EXITED\nexit_code=0')
if [ "$create_status" -eq 0 ] && [ "$run_status" -eq 0 ] \
    && [ "$command_status" -eq 0 ] && [ "$inspect_output" = "$expected" ]; then
    pass 'spaces and shell syntax remain inert argv data'
else
    fail 'spaces and shell syntax remain inert argv data'
fi

runner_link=$test_root/runner-link
ln -s "$exact_runner" "$runner_link"
export TINYBOX_RUNNER=$runner_link
run_controller run argvcase -- /bin/tool 'two words' '*' 'semi;colon' ''
if [ "$command_status" -ne 0 ]; then
    pass 'a symlink is not accepted as the configured runner file'
else
    fail 'a symlink is not accepted as the configured runner file'
fi

printf '1..%s\n' "$checks"
if [ "$failures" -ne 0 ]; then
    printf '# %s of %s adversarial checks failed\n' "$failures" "$checks"
    exit 1
fi
printf '# all %s adversarial checks passed\n' "$checks"
