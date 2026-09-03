# Starter implementation

The starter has a complete, position-aware lexer and explicit compiler/VM
interfaces.  It builds a useful `--tokens` executable; compilation and execution
are intentional stubs.

```sh
make -C starter clean all
starter/build/emberc --tokens public_tests/cases/precedence.ec
```

Suggested implementation order:

1. Add bytecode emission, source locations, and patching in `src/compiler.c`.
2. Implement the precedence ladder, scoped locals, and the checked 256-level
   syntax budget.
3. Implement checked dispatch in `src/vm.c`, preserving the source path and
   opcode line/column for every runtime diagnostic.
4. Connect CLI modes in `src/main.c` without weakening `--tokens`.

The starter `Bytecode` shape is deliberately minimal.  To satisfy the runtime
diagnostic contract, redesign it to retain a line and column per word (or
equivalent structured locations) and carry `source_path` through execution.
The VM API already accepts that path.  A zero instruction budget is valid and
must fail before the first opcode, not during option parsing.

Keep newly introduced interfaces in `include/ember.h`.  Do not encode expected
test output in the interpreter.
