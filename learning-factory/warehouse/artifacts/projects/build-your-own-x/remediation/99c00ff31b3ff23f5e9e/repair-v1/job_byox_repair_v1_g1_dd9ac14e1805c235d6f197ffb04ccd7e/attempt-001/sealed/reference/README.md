# Sealed reference implementation

`src/mica.c` is an independently written C11 implementation of the complete
learner contract. It contains a bounded lexer, recursive-descent parser, shared
AST validation, tree-walking interpreter, and x86-64 System V assembly emitter.

Build and exercise it from the repository root:

```bash
make -C sealed/reference clean all
MICA_BIN=sealed/reference/mica python3 public_tests/test_public.py
python3 sealed/reference_tests/test_reference.py
```

The native-output tests require GNU-compatible `cc` and an x86-64 System V
userspace. The implementation initializes every allocated variable slot to zero;
this defines the observable value of a declaration inside a branch that was not
executed but is visible at a later source position.
