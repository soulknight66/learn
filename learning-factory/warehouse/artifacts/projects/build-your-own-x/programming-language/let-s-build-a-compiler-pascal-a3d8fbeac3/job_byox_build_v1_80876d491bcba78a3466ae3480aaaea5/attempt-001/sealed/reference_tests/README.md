# Sealed reference tests

These evaluator-owned black-box tests extend the public suite with boundary
locations, compile-time errors in unreachable code, unexecuted declarations,
associativity, step exhaustion, and output preservation after failure.

From the repository root:

```bash
make -C sealed/reference
MICA_BIN="$PWD/sealed/reference/bin/mica" python3 public_tests/run_tests.py
MICA_BIN="$PWD/sealed/reference/bin/mica" \
  python3 sealed/reference_tests/run_reference_tests.py
```

The tests use temporary files and bounded subprocess timeouts. They are reference
evidence only after execution by a harness with a Pascal compiler; they were not
run natively on the generation host.
