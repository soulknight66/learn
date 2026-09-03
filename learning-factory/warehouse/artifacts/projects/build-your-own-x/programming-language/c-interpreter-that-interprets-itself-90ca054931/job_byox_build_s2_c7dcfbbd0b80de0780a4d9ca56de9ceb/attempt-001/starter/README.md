# Starter implementation

The starter has a complete, position-aware lexer and explicit compiler/VM
interfaces.  It builds a useful `--tokens` executable; compilation and execution
are intentional stubs.

```sh
make -C starter clean all
starter/build/emberc --tokens public_tests/cases/precedence.ec
```

Suggested implementation order:

1. Add bytecode emission and patching in `src/compiler.c`.
2. Implement the precedence ladder and scoped local table.
3. Implement checked dispatch in `src/vm.c`.
4. Connect CLI modes in `src/main.c` without weakening `--tokens`.

Keep newly introduced interfaces in `include/ember.h`.  Do not encode expected
test output in the interpreter.
