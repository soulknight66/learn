# Public behavior tests

These tests launch a compiled Mica executable as a subprocess. They cover normal
evaluation, control flow, static name errors, arithmetic failures, debug modes,
and exit-code separation. They do not import Pascal units or prescribe an
internal architecture.

```bash
MICA_BIN="$PWD/starter/bin/mica" python3 public_tests/run_tests.py
```

The harness uses a fresh temporary source file per case, passes arguments as an
array, captures both output streams, and applies a five-second timeout. Set
`MICA_BIN` to another implementation to test it. Missing or non-executable paths
are reported as test setup failures.

Passing this suite is useful evidence, not proof of full conformance. Independent
validation may vary whitespace, nesting, names, values, malformed tokens, and
resource-limit cases.
