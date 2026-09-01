# Sealed reference tests

This suite drives an executable strictly through its command-line interface. It checks successful
evaluation, order, signed division/remainder, forward calls, source failures, runtime arithmetic
faults, exact and excessive token/nesting limits, frame limits, step limits, usage, and the nested
interpreter demonstration.

Run from the repository root:

```sh
python3 sealed/reference_tests/run_tests.py sealed/reference/build/minic
```

The suite is deterministic and dependency-free. Generated boundary inputs live only in a temporary
directory below the repository and are removed by the runner. It shares the public runner's POSIX
process-group containment and 65,536-byte per-stream capture limit, with an aggregate 180-second
wall deadline. It is reference evidence only; independent validation remains required, and this is
not an exhaustive security or conformance suite.
