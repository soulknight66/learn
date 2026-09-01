# Sealed reference implementation

This directory contains an independently written compiler and stack VM for the public Pebble contract.
It is evaluator material, not a template for learner submissions. The representation favors explicit
bounds and readable invariants over byte density: instructions carry source positions, jumps use
absolute instruction indexes, and symbol slots remain stable for a program's lifetime.

Build and run tests from the repository root:

```sh
make -C sealed/reference clean all
make -C sealed/reference test
```

Successful local execution is only recorded evidence; it does not change the repository's
`GENERATED` + `PARTIAL` labels or replace independent validation.
