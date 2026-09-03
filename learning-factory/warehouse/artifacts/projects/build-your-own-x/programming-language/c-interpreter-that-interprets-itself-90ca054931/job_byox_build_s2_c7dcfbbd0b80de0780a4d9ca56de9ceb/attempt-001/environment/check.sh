#!/bin/sh
set -eu

CC_BIN=${CC_BIN:-/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc}
PYTHON_BIN=${PYTHON_BIN:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}

"$CC_BIN" --version | sed -n '1p'
"$PYTHON_BIN" --version

printf '%s\n' 'int main(void) { return 0; }' | \
    "$CC_BIN" -x c -std=c17 -Wall -Wextra -Werror -pedantic \
    -fsyntax-only -
printf '%s\n' 'C17 syntax smoke check: PASS'
