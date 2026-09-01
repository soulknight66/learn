#!/usr/bin/env bash
# Opt-in real-host probe.  It creates its rootfs from a tiny locally compiled
# static program and never contacts a network service.

set -uo pipefail

readonly TEST_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
readonly CLI="$(cd -- "$TEST_DIR/../reference" && pwd -P)/minictr"

if [[ ${MINICTR_RUN_REAL_TESTS:-0} != 1 ]]; then
    printf 'SKIP: set MINICTR_RUN_REAL_TESTS=1 to exercise host namespaces\n'
    exit 0
fi
for tool in cc uname unshare mount chroot env timeout; do
    if ! command -v -- "$tool" >/dev/null 2>&1; then
        printf 'SKIP: required host tool is unavailable: %s\n' "$tool"
        exit 0
    fi
done

TEST_TMP_BASE=$(cd -- "${TMPDIR:-/tmp}" >/dev/null 2>&1 && pwd -P) || exit 1
readonly TEST_TMP_BASE
TEST_TMP=$(mktemp -d "$TEST_TMP_BASE/minictr-real-test.XXXXXX") || exit 1
readonly TEST_TMP
signal_runner=
cleanup() {
    if [[ -n $signal_runner ]] && kill -0 "$signal_runner" 2>/dev/null; then
        kill -KILL "$signal_runner" 2>/dev/null || true
        wait "$signal_runner" 2>/dev/null || true
    fi
    chmod -R u+rwX -- "$TEST_TMP" 2>/dev/null || true
    rm -rf -- "$TEST_TMP"
}
trap cleanup EXIT HUP INT TERM
mkdir -p -- "$TEST_TMP/rootfs/bin" "$TEST_TMP/rootfs/proc"

architecture=$(uname -m)
case $architecture in
    x86_64)
        printf '%s\n' \
            '.section .rodata' \
            'message: .ascii "namespace-ok\n"' \
            '.set message_len, . - message' \
            '.section .text' \
            '.global _start' \
            '.type _start,@function' \
            '_start:' \
            '  mov $1, %rax' \
            '  mov $1, %rdi' \
            '  lea message(%rip), %rsi' \
            '  mov $message_len, %rdx' \
            '  syscall' \
            '  mov $60, %rax' \
            '  xor %rdi, %rdi' \
            '  syscall' \
            '.size _start, . - _start' \
            '.section .note.GNU-stack,"",@progbits' > "$TEST_TMP/probe.S"
        printf '%s\n' \
            '.section .rodata' \
            'ready_message: .ascii "payload-ready\n"' \
            '.set ready_len, . - ready_message' \
            'term_message: .ascii "payload-received-TERM\n"' \
            '.set term_len, . - term_message' \
            '.section .data' \
            '.balign 8' \
            'term_action:' \
            '  .quad term_handler' \
            '  .quad 0x04000000' \
            '  .quad signal_restorer' \
            '  .quad 0' \
            '.section .text' \
            '.global _start' \
            '.type _start,@function' \
            '_start:' \
            '  mov $13, %rax' \
            '  mov $15, %rdi' \
            '  lea term_action(%rip), %rsi' \
            '  xor %rdx, %rdx' \
            '  mov $8, %r10' \
            '  syscall' \
            '  test %rax, %rax' \
            '  js setup_failed' \
            '  mov $1, %rax' \
            '  mov $1, %rdi' \
            '  lea ready_message(%rip), %rsi' \
            '  mov $ready_len, %rdx' \
            '  syscall' \
            'wait_for_signal:' \
            '  mov $34, %rax' \
            '  syscall' \
            '  jmp wait_for_signal' \
            'term_handler:' \
            '  mov $1, %rax' \
            '  mov $1, %rdi' \
            '  lea term_message(%rip), %rsi' \
            '  mov $term_len, %rdx' \
            '  syscall' \
            '  mov $60, %rax' \
            '  xor %rdi, %rdi' \
            '  syscall' \
            'signal_restorer:' \
            '  mov $15, %rax' \
            '  syscall' \
            'setup_failed:' \
            '  mov $60, %rax' \
            '  mov $70, %rdi' \
            '  syscall' \
            '.size _start, . - _start' \
            '.section .note.GNU-stack,"",@progbits' > "$TEST_TMP/term-probe.S"
        signal_probe_supported=1
        ;;
    aarch64|arm64)
        printf '%s\n' \
            '.section .rodata' \
            'message: .ascii "namespace-ok\n"' \
            '.section .text' \
            '.global _start' \
            '.type _start,%function' \
            '_start:' \
            '  mov x0, #1' \
            '  adrp x1, message' \
            '  add x1, x1, :lo12:message' \
            '  mov x2, #13' \
            '  mov x8, #64' \
            '  svc #0' \
            '  mov x0, #0' \
            '  mov x8, #93' \
            '  svc #0' \
            '.size _start, . - _start' \
            '.section .note.GNU-stack,"",%progbits' > "$TEST_TMP/probe.S"
        signal_probe_supported=0
        ;;
    *)
        printf 'SKIP: static probe assembly is unavailable for architecture: %s\n' "$architecture"
        exit 0
        ;;
esac

if ! timeout --kill-after=2 15 cc -nostdlib -static -Wl,--build-id=none \
    -o "$TEST_TMP/rootfs/bin/probe" "$TEST_TMP/probe.S" \
    >"$TEST_TMP/compiler.out" 2>"$TEST_TMP/compiler.err"; then
    compiler_reason=
    IFS= read -r compiler_reason < "$TEST_TMP/compiler.err" || true
    printf 'SKIP: host compiler cannot produce a static probe binary: %s\n' \
        "${compiler_reason:-unknown compiler error}"
    exit 0
fi

if (( signal_probe_supported == 1 )); then
    if ! timeout --kill-after=2 15 cc -nostdlib -static -Wl,--build-id=none \
        -o "$TEST_TMP/rootfs/bin/term-probe" "$TEST_TMP/term-probe.S" \
        >"$TEST_TMP/term-compiler.out" 2>"$TEST_TMP/term-compiler.err"; then
        compiler_reason=
        IFS= read -r compiler_reason < "$TEST_TMP/term-compiler.err" || true
        printf 'FAIL: host compiler cannot produce the static TERM probe: %s\n' \
            "${compiler_reason:-unknown compiler error}" >&2
        exit 1
    fi
fi

# Probe the exact namespace set first.  Restricted CI hosts commonly disable
# one or more of these operations even when util-linux is installed.
if ! timeout --kill-after=2 10 unshare \
    --user --map-root-user --mount --pid --uts --ipc --net --fork -- true \
    >"$TEST_TMP/unshare.out" 2>"$TEST_TMP/unshare.err"; then
    printf 'SKIP: host policy denies the required namespace set\n'
    exit 0
fi

MINICTR_HOME=$TEST_TMP/state "$CLI" create probe "$TEST_TMP/rootfs" || exit 1
output=$(MINICTR_HOME=$TEST_TMP/state timeout --kill-after=2 15 \
    "$CLI" run probe /bin/probe) || {
    status=$?
    printf 'FAIL: real namespace run exited %s\n' "$status" >&2
    exit "$status"
}
if [[ $output != namespace-ok ]]; then
    printf 'FAIL: unexpected probe output: <%s>\n' "$output" >&2
    exit 1
fi
MINICTR_HOME=$TEST_TMP/state "$CLI" delete probe || exit 1
printf 'PASS: rootless user/mount/PID/UTS/IPC/network namespace probe\n'

if (( signal_probe_supported == 1 )); then
    MINICTR_HOME=$TEST_TMP/state "$CLI" create term-probe "$TEST_TMP/rootfs" || exit 1
    MINICTR_HOME=$TEST_TMP/state "$CLI" run term-probe /bin/term-probe \
        >"$TEST_TMP/term.out" 2>"$TEST_TMP/term.err" &
    signal_runner=$!
    payload_ready=0
    for ((attempt = 0; attempt < 400; attempt += 1)); do
        if [[ -f $TEST_TMP/term.out ]] && [[ $(<"$TEST_TMP/term.out") == *payload-ready* ]]; then
            payload_ready=1
            break
        fi
        kill -0 "$signal_runner" 2>/dev/null || break
        sleep 0.01
    done
    if (( payload_ready == 0 )); then
        printf '%s\n' 'FAIL: real isolated TERM probe did not become ready' >&2
        exit 1
    fi
    kill -TERM "$signal_runner"
    for ((attempt = 0; attempt < 400; attempt += 1)); do
        kill -0 "$signal_runner" 2>/dev/null || break
        sleep 0.01
    done
    if kill -0 "$signal_runner" 2>/dev/null; then
        printf '%s\n' 'FAIL: wrapper did not finish after TERM within the bound' >&2
        exit 1
    fi
    wait "$signal_runner" 2>/dev/null
    signal_status=$?
    signal_runner=
    term_output=$(<"$TEST_TMP/term.out")
    if (( signal_status != 143 )); then
        printf 'FAIL: TERM wrapper status was %s, expected 143\n' "$signal_status" >&2
        exit 1
    fi
    if [[ $term_output != $'payload-ready\npayload-received-TERM' ]]; then
        printf 'FAIL: isolated payload did not observe TERM: <%s>\n' "$term_output" >&2
        exit 1
    fi
    if [[ -s $TEST_TMP/term.err ]]; then
        printf 'FAIL: TERM probe wrote stderr: <%s>\n' "$(<"$TEST_TMP/term.err")" >&2
        exit 1
    fi
    term_ps=$(MINICTR_HOME=$TEST_TMP/state "$CLI" ps) || exit 1
    if [[ $term_ps != *$'term-probe\tCREATED\t-'* ]]; then
        printf '%s\n' 'FAIL: TERM cleanup did not restore CREATED state' >&2
        exit 1
    fi
    MINICTR_HOME=$TEST_TMP/state "$CLI" delete term-probe || exit 1
    printf 'PASS: real default isolator delivered TERM to the payload and restored state\n'
else
    printf 'SKIP: static TERM delivery probe is not implemented for %s\n' "$architecture"
fi
