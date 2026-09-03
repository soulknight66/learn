#!/bin/sh
set -eu

PYTHON_BIN=${PYTHON_BIN:-/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3}
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN=python3
fi
export PYTHONDONTWRITEBYTECODE=1

make -C sealed/reference all
make -C sealed/reference_tests clean all
sealed/reference_tests/build/test_vm
exec "$PYTHON_BIN" -m unittest -v sealed.reference_tests.test_private
