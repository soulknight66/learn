# Sealed reference tests

The dependency-free reference harness adds token-location, numeric-range boundaries, dense-bytecode
evaluation-limit parity, whole-program malformed-bytecode validation, shadowing, error-location,
CLI-independent, and deterministic differential cases beyond the public examples. The suite is
deterministic and performs no network or filesystem mutation.

Run from the repository root:

```bash
sealed/reference_tests/run.sh
```
