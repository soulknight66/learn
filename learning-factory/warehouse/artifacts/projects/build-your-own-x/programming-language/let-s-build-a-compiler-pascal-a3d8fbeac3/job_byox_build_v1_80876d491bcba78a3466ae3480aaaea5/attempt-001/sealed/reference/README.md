# Sealed reference implementation

This directory contains an independently generated Free Pascal implementation of
the Mica lexer, single-pass compiler, and stack VM. It is evaluator material and
must not be copied into learner-visible paths.

Build from this directory with Free Pascal 3.2.x:

```bash
make
./bin/mica ../../sealed/reference_tests/cases/factorial.mica
```

Run the sealed black-box suite from the repository root:

```bash
make -C sealed/reference
MICA_BIN="$PWD/sealed/reference/bin/mica" \
  python3 sealed/reference_tests/run_reference_tests.py
```

The source uses only standard units. Compilation and native execution were not
possible on the generation host because `fpc` was absent; see `VALIDATION.md`.
Consequently this is a reference candidate pending independent validation, not a
claim of tested correctness.

Implementation outline:

- `lexer.pas` performs checked scanning with one-based byte locations.
- `compiler.pas` resolves flat slots and emits bytecode while parsing.
- `vm.pas` enforces arithmetic bounds, operand order, jump checks, and the step
  budget.
- `mica.pas` owns file I/O, debug listings, diagnostics, and exit codes.
