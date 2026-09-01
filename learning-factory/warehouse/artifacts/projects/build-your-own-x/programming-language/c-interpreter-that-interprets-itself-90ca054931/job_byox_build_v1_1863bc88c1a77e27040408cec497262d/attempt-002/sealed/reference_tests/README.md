# Sealed reference tests

This suite drives an executable strictly through its command-line interface. It checks successful
evaluation, order, signed division/remainder, forward calls, source failures, runtime arithmetic
faults, frame limits, step limits, usage, and the nested interpreter demonstration.

Run from the repository root:

```sh
python3 sealed/reference_tests/run_tests.py sealed/reference/build/minic
```

The suite is deterministic and dependency-free. It is reference evidence only; independent
validation remains required, and this is not an exhaustive security or conformance suite.
