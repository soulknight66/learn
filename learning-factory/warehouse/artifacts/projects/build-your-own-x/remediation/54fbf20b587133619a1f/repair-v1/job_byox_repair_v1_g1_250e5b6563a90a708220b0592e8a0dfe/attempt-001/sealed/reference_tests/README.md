# Pebble sealed reference tests

This directory contains deterministic black-box and format-level tests for the independent sealed
reference in `sealed/reference/`. The suite covers public token and AST shapes, precedence and
syntax failures, interpreter/VM parity, global bindings and control flow, runtime error codes,
finite-number overflow, deterministic constant-pool bytecode, backend dispatch, exact per-backend
instruction/work limits, and malformed bytecode.

From the repository root, run:

```bash
node --test sealed/reference_tests/*.test.mjs
```

The suite uses only `node:test` and `node:assert`; it has no package-install step or third-party
dependencies.
