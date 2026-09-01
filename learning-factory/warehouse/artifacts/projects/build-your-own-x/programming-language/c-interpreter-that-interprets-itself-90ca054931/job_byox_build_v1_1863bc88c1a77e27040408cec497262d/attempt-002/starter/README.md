# Starter scaffold

This scaffold builds successfully but intentionally stops after safe source loading. It is not a
solution and is expected to fail the behavioral public tests until you implement the language.

## Build

```sh
make -C starter clean all
python3 public_tests/run_tests.py starter/build/minic
```

## Suggested progression

1. Replace the placeholder in `src/interpreter.c` with a lexer. Write token-dump tests locally.
2. Add the expression precedence layers, then declarations and print statements.
3. Lower control flow to jumps and patch their targets.
4. Add function metadata, unresolved-call patches, and bounded frames.
5. Add checked arithmetic and enforce `--max-steps` at the bytecode dispatch boundary.
6. Create your own nested interpreter fixture following requirement 6.6.

You may split the placeholder into modules. Keep a narrow public entry point in `minic.h`, return
the specified exit categories, and do not weaken the compile warnings. Do not inspect sealed
material in a learner attempt.
