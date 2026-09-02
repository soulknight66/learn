# Starter workspace

This directory is the learner's implementation area. It builds a deliberately
incomplete `pebble` executable while preserving the required CLI.

```bash
make -C starter
starter/pebble eval starter/examples/count.pb
python3 public_tests/run_tests.py
```

Suggested milestones:

- replace the lexer placeholder and retain token locations;
- define owned expression and statement AST nodes;
- parse the grammar with explicit nesting limits;
- resolve every variable use before execution or code generation;
- implement checked evaluation with a deterministic step budget;
- emit System V AMD64 assembly and publish it atomically.

The public tests can be pointed at another binary with `PEBBLE_BIN=/path/to/bin`.
Do not add reference answers, expected hidden cases, or sealed material here.
