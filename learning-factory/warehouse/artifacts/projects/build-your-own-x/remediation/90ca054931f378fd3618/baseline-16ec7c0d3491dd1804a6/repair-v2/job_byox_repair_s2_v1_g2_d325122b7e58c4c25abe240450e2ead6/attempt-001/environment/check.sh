#!/bin/sh
set -eu

CC_BIN=${CC_BIN:-/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc}
BINUTILS_DIR=${BINUTILS_DIR:-/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin}
PYTHON_BIN=${PYTHON_BIN:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}
LD_BIN=${BINUTILS_DIR%/}/ld
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

if [ ! -x "$LD_BIN" ]; then
    printf '%s\n' "configured linker is not executable: $LD_BIN" >&2
    exit 1
fi

"$CC_BIN" --version | sed -n '1p'
"$LD_BIN" --version | sed -n '1p'
"$PYTHON_BIN" --version

RESOLVED_LD=$("$CC_BIN" "-B${BINUTILS_DIR%/}/" -print-prog-name=ld)
if [ "$RESOLVED_LD" != "$LD_BIN" ]; then
    printf '%s\n' "GCC resolved an unexpected linker: $RESOLVED_LD" >&2
    exit 1
fi
printf '%s\n' "GCC linker: $RESOLVED_LD"

CHECK_DIR=$(/usr/bin/mktemp -d "$SCRIPT_DIR/.link-smoke.XXXXXX")
cleanup() {
    /usr/bin/rm -f -- "$CHECK_DIR/smoke.c" "$CHECK_DIR/smoke"
    /usr/bin/rmdir -- "$CHECK_DIR"
}
trap cleanup 0
trap 'exit 1' 1 2 15

printf '%s\n' 'int main(void) { return 0; }' > "$CHECK_DIR/smoke.c"
"$CC_BIN" "-B${BINUTILS_DIR%/}/" -x c -std=c17 \
    -Wall -Wextra -Werror -pedantic "$CHECK_DIR/smoke.c" \
    -o "$CHECK_DIR/smoke"
"$CHECK_DIR/smoke"
printf '%s\n' 'C17 compile/link/execute smoke check: PASS'
