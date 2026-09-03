#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: sealed/reference_tests/run.sh REFERENCE_DIR" >&2
    exit 2
fi

case "$1" in
    /*) reference=$1 ;;
    *) reference=$(pwd)/$1 ;;
esac

test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
compiler=${CC:-cc}
python=${PYTHON:-python3}
build_dir="$test_dir/.build"

mkdir -p "$build_dir"
trap 'rm -f "$build_dir/test_reference" "$build_dir/probe"' EXIT HUP INT TERM

"${MAKE:-make}" -C "$reference" clean all CC="$compiler"

"$compiler" -std=c17 -D_POSIX_C_SOURCE=200809L \
    -Wall -Wextra -Wpedantic -Werror -O2 -g \
    -I"$reference/include" \
    "$test_dir/test_reference.c" "$reference/src/lexer.c" \
    "$reference/src/parser.c" "$reference/src/execute.c" \
    -o "$build_dir/test_reference"

"$compiler" -std=c17 -D_POSIX_C_SOURCE=200809L \
    -Wall -Wextra -Wpedantic -Werror -O2 -g \
    "$test_dir/probe.c" -o "$build_dir/probe"

"$build_dir/test_reference"
"$python" "$test_dir/test_cli.py" "$reference/minish" "$build_dir/probe"
"$python" "$test_dir/test_pty.py" "$reference/minish"
