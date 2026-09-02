# Sealed reference tests

These maintainer-only tests extend the public contract with numeric boundaries, resource limits, name-resolution timing, exact modes, error codes, output preservation, and malformed-bytecode defense.

Run both layers after building the reference:

```sh
python3 public_tests/run_tests.py --binary sealed/reference/build/sprig
python3 sealed/reference_tests/run_tests.py --binary sealed/reference/build/sprig
make -C sealed/reference_tests clean test
```

Passing locally is evidence only for the commands recorded in `VALIDATION.md`; independent validation remains mandatory.
