#!/usr/bin/env bash
set -u

script_dir=$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo_dir=$(CDPATH= cd -- "$script_dir/.." && pwd -P)
target=${1:-"$repo_dir/starter/minictr"}

if [[ ! -x $target ]]; then
    printf 'adversarial: target is not executable: %s\n' "$target" >&2
    exit 2
fi
target=$(CDPATH= cd -- "$(dirname -- "$target")" && printf '%s/%s\n' "$PWD" "$(basename -- "$target")")
timeout_bin=$(command -v timeout) || {
    printf 'adversarial: the timeout utility is required\n' >&2
    exit 2
}

work_base=$(CDPATH= cd -- "${TMPDIR:-/tmp}" && pwd -P) || {
    printf 'adversarial: cannot resolve the temporary directory\n' >&2
    exit 2
}
work=$(mktemp -d "$work_base/minictr-adversarial.XXXXXX") || exit 2
background_pid=
cleanup() {
    if [[ -n ${FAKE_RELEASE_FILE:-} ]]; then
        : >"$FAKE_RELEASE_FILE" 2>/dev/null || true
    fi
    if [[ -n $background_pid ]] && kill -0 "$background_pid" 2>/dev/null; then
        kill -TERM "$background_pid" 2>/dev/null || true
        for ((cleanup_attempt = 0; cleanup_attempt < 100; cleanup_attempt += 1)); do
            kill -0 "$background_pid" 2>/dev/null || break
            sleep 0.01
        done
        kill -KILL "$background_pid" 2>/dev/null || true
        wait "$background_pid" 2>/dev/null || true
    fi
    rm -rf -- "$work"
}
trap cleanup EXIT HUP INT TERM

export MINICTR_HOME="$work/state"
rootfs="$work/root fs"
mkdir -p -- "$rootfs" "$MINICTR_HOME"

last_out="$work/stdout"
last_err="$work/stderr"
last_status=0
passes=0
failures=0

run_capture() {
    set +e
    "$timeout_bin" --signal=TERM --kill-after=1s 6s "$@" >"$last_out" 2>"$last_err"
    last_status=$?
    set -e
}

pass() {
    printf 'ok - %s\n' "$1"
    ((passes += 1))
}

fail() {
    printf 'not ok - %s\n' "$1"
    if [[ -s $last_err ]]; then
        sed 's/^/  stderr: /' "$last_err"
    fi
    ((failures += 1))
}

expect_success() {
    local label=$1
    shift
    run_capture "$@"
    if ((last_status == 0)); then
        pass "$label"
    else
        fail "$label (status $last_status)"
    fi
}

expect_silent_success() {
    local label=$1
    shift
    run_capture "$@"
    if ((last_status == 0)) && [[ ! -s $last_out && ! -s $last_err ]]; then
        pass "$label"
    else
        fail "$label (expected silent status 0, got $last_status)"
    fi
}

expect_failure() {
    local label=$1
    shift
    run_capture "$@"
    if ((last_status != 0)) && [[ ! -s $last_out ]] && grep -q '^minictr:' "$last_err"; then
        pass "$label"
    else
        fail "$label (expected empty stdout and a nonzero minictr error)"
    fi
}

printf '1..34\n'

expect_silent_success 'create accepts a valid name and absolute rootfs' \
    "$target" create alpha "$rootfs"
expect_failure 'duplicate create is rejected' \
    "$target" create alpha "$rootfs"
expect_failure 'a missing rootfs is rejected' \
    "$target" create missing "$work/does-not-exist"
expect_failure 'a relative rootfs is rejected' \
    "$target" create relative relative-root
expect_failure 'the host root is rejected' \
    "$target" create host-root /

for invalid_name in '../escape' 'bad/name' '.' '..' '.hidden' '_leading' 'two words'; do
    expect_failure "invalid name is rejected: $invalid_name" \
        "$target" create "$invalid_name" "$rootfs"
done

long_name=$(printf '%065d' 0)
expect_failure 'a 65-character name is rejected' \
    "$target" create "$long_name" "$rootfs"
max_name=m$(printf '%063d' 0)
expect_silent_success 'a 64-character name is accepted' \
    "$target" create "$max_name" "$rootfs"
expect_silent_success 'a 64-character name can be deleted' \
    "$target" delete "$max_name"
expect_silent_success 'punctuation inside a valid name is accepted' \
    "$target" create 'A_b.c-9' "$rootfs"
expect_silent_success 'delete is silent for a created instance' \
    "$target" delete 'A_b.c-9'
expect_failure 'delete rejects an unknown instance' \
    "$target" delete 'not-created'
expect_failure 'run rejects an unknown instance before isolation' \
    "$target" run 'not-created' true

control_rootfs="$work/"$'line\nbreak'
mkdir -- "$control_rootfs"
expect_failure 'a line break in ROOTFS is rejected' \
    "$target" create control-root "$control_rootfs"

expect_success 'ps succeeds' "$target" ps
if awk -F '\t' '
    NR == 1 { good_header = ($1 == "NAME" && $2 == "STATUS" && $3 == "PID" && $4 == "ROOTFS") }
    NR > 1 && $1 == "alpha" && $2 == "CREATED" && $3 == "-" { found = 1 }
    END { exit !(good_header && found) }
' "$last_out"; then
    pass 'ps has the contract header and the created row'
else
    fail 'ps has the contract header and the created row'
fi

export MINICTR_ISOLATOR="$script_dir/fixtures/capture-isolator"
vanishing_rootfs="$work/vanishing-rootfs"
mkdir -- "$vanishing_rootfs"
expect_silent_success 'create records a disposable rootfs' \
    "$target" create vanished "$vanishing_rootfs"
export CAPTURE_FILE="$work/unexpected-isolator.capture"
rmdir -- "$vanishing_rootfs"
expect_failure 'run rechecks a rootfs that disappeared after create' \
    "$target" run vanished should-not-launch
if [[ ! -e $CAPTURE_FILE ]]; then
    pass 'missing rootfs fails before the isolator is invoked'
else
    fail 'missing rootfs fails before the isolator is invoked'
fi
expect_silent_success 'registration with a missing rootfs remains deletable' \
    "$target" delete vanished

export CAPTURE_FILE="$work/argv.capture"
export FAKE_STDOUT='helper stdout'
export FAKE_STDERR='helper stderr'
export FAKE_STATUS=23
run_capture "$target" run alpha 'command with spaces' 'argument one' '*' ''
if ((last_status == 23)) && [[ $(<"$last_out") == 'helper stdout' ]] && \
        [[ $(<"$last_err") == 'helper stderr' ]]; then
    pass 'run preserves helper output and nonzero status'
else
    fail 'run preserves helper output and nonzero status'
fi

mapfile -d '' -t captured <"$CAPTURE_FILE"
expected=("$rootfs" 'command with spaces' 'argument one' '*' '')
if ((${#captured[@]} == ${#expected[@]})); then
    argv_ok=1
    for ((i = 0; i < ${#expected[@]}; i += 1)); do
        if [[ ${captured[i]} != "${expected[i]}" ]]; then
            argv_ok=0
        fi
    done
else
    argv_ok=0
fi
if ((argv_ok)); then
    pass 'run passes rootfs, command, and arguments as exact argv elements'
else
    fail 'run passes rootfs, command, and arguments as exact argv elements'
fi

unset FAKE_STDOUT FAKE_STDERR FAKE_STATUS
export FAKE_READY_FILE="$work/isolator.ready"
export FAKE_RELEASE_FILE="$work/isolator.release"
"$timeout_bin" --signal=TERM --kill-after=1s 8s \
    "$target" run alpha hold-open >"$work/background.out" 2>"$work/background.err" &
run_pid=$!
background_pid=$run_pid
ready=0
for ((i = 0; i < 500; i += 1)); do
    if [[ -e $FAKE_READY_FILE ]]; then
        ready=1
        break
    fi
    if ! kill -0 "$run_pid" 2>/dev/null; then
        break
    fi
    sleep 0.01
done
if ((ready)); then
    run_capture "$target" ps
    if ((last_status == 0)) && awk -F '\t' \
            '$1 == "alpha" && $2 == "RUNNING" && $3 ~ /^[1-9][0-9]*$/ { found = 1 }
             END { exit !found }' "$last_out"; then
        pass 'ps reports a verified RUNNING owner while the helper is active'
    else
        fail 'ps reports a verified RUNNING owner while the helper is active'
    fi
    expect_failure 'delete refuses an instance with an active run' \
        "$target" delete alpha
else
    : >"$FAKE_RELEASE_FILE"
    wait "$run_pid" 2>/dev/null || true
    fail 'delete refuses an instance with an active run (run never became ready)'
fi
: >"$FAKE_RELEASE_FILE"
set +e
wait "$run_pid"
background_status=$?
set -e
background_pid=
if ((background_status == 0)); then
    pass 'the held run completes after release'
else
    cp -- "$work/background.err" "$last_err"
    fail "the held run completes after release (status $background_status)"
fi
unset FAKE_READY_FILE FAKE_RELEASE_FILE

expect_silent_success 'delete succeeds after the run completes' \
    "$target" delete alpha
expect_success 'ps succeeds after deletion' "$target" ps
if [[ $(wc -l <"$last_out") -eq 1 ]]; then
    pass 'ps contains only its header after deletion'
else
    fail 'ps contains only its header after deletion'
fi

if ((failures > 0)); then
    printf '# %d passed; %d failed\n' "$passes" "$failures"
    exit 1
fi
printf '# %d passed; 0 failed\n' "$passes"
