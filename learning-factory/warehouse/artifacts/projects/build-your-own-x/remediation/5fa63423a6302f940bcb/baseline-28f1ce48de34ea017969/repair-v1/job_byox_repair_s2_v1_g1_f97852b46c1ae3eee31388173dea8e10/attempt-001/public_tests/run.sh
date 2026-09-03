#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
    echo "usage: public_tests/run.sh IMPLEMENTATION_DIR" >&2
    exit 2
fi

case "$1" in
    /*) implementation=$1 ;;
    *) implementation=$(pwd)/$1 ;;
esac

test_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
compiler=${CC:-cc}
python=${PYTHON:-python3}

"${MAKE:-make}" -C "$implementation" clean all CC="$compiler"

build_dir="$implementation/.public-test-build"
mkdir -p "$build_dir"
trap 'rm -f "$build_dir/test_core"' EXIT HUP INT TERM

"$compiler" -std=c17 -D_POSIX_C_SOURCE=200809L \
    -Wall -Wextra -Wpedantic -Werror -O2 -g \
    -I"$implementation/include" \
    "$test_dir/test_core.c" \
    "$implementation/src/lexer.c" "$implementation/src/parser.c" \
    -o "$build_dir/test_core"

"$build_dir/test_core"
"$python" "$test_dir/test_cli.py" "$implementation/minish"
