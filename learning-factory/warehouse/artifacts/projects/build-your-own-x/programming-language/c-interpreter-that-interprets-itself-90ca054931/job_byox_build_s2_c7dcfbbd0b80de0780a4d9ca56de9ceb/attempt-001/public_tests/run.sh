#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN=python3
fi
export PYTHONDONTWRITEBYTECODE=1

if [ "${1:-}" = "--lexer-only" ]; then
    export EMBER_LEXER_ONLY=1
    shift
fi

exec "$PYTHON_BIN" -m unittest -v public_tests.test_public "$@"
