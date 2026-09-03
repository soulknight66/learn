# Sealed reference implementation

This directory contains an independently written complete implementation of the specified Sprig compiler and VM. It is validator/maintainer material, not a learner input.

The implementation uses a one-token recursive-descent parser, compile-time slot resolution, fixed-capacity bytecode, and checked `int64_t` arithmetic. It is intentionally small enough to review; it is not claimed production-ready.

Maintainer commands from the repository root:

```sh
make -C sealed/reference clean all
python3 sealed/reference_tests/run_tests.py --binary sealed/reference/build/sprig
```
