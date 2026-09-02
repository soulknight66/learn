# Sealed reference implementation

`forth.S` is an independently generated, freestanding x86-64 implementation of the public Cinder
contract. It contains a byte tokenizer, checked decimal parser, fixed primitive and user
dictionaries, cell compiler with typed backpatch stack, data and return stacks, a fuel-bounded VM,
and direct Linux I/O.

Build from the repository root:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py sealed/reference/forth.S -o sealed/reference/build/cinder-reference
```

This is evaluator-only solution material. Its presence and local tests do not confer an independent
validation label.
