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
trap 'chmod -R u+rwX -- "$TEST_TMP" 2>/dev/null || true; rm -rf -- "$TEST_TMP"' EXIT
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
