# Sealed reference implementation

This directory contains an independently written Ruby implementation of the Pebble contract. It is evaluator material, not learner scaffolding.

The implementation is split into lexer, parser, compiler, and VM stages under `lib/pebble/`. It uses numeric lexical-scope slots, patches forward jumps after emitting their bodies, validates every instruction before execution, checks runtime types and 32-bit arithmetic, and applies a deterministic instruction budget.

Evaluator commands from the repository root:

```sh
PEBBLE_LIB=sealed/reference/lib ruby public_tests/test_public.rb
ruby -Isealed/reference/lib sealed/reference_tests/test_reference.rb
ruby sealed/reference/bin/pebble sealed/reference_tests/fixtures/countdown.peb
```

This is a teaching reference, not a production claim. Remaining hardening work is cataloged in `sealed/production/PRODUCTIONIZATION.md` and `sealed/REVIEW.md`.
