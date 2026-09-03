# Sealed reference implementation

This directory contains an independently written C17 lexer, single-pass
compiler, checked stack VM, CLI, and a guest-language interpreter tower.  It is
validator material, not learner material.

Build from the repository root:

```sh
make -C sealed/reference clean all
```

Useful validation commands:

```sh
sealed/reference/build/emberc-ref public_tests/cases/factorial.ec
sealed/reference/build/emberc-ref --emit \
  sealed/reference/self/tower.ec /tmp/tower.bytecode
sealed/reference/build/emberc-ref --tower sealed/reference/self/tower.ec
```

The expected tower output is one line, `4242`.  The outer native VM runs the
compiled guest interpreter with mode zero.  That interpreter reads its own
bytecode through `arg`, simulates it, and maps the simulated program's
`arg(0)` to one.  The same bytecode consequently takes its finite base branch
and prints the marker.

This is intentionally labeled partial: it proves a bytecode semantic tower,
not parsing of the reference C source by itself and not ISO C conformance.  The
guest tower also reserves host heap regions for simulated locals and stack, so
its nested heap capacity is smaller than the native VM's.
