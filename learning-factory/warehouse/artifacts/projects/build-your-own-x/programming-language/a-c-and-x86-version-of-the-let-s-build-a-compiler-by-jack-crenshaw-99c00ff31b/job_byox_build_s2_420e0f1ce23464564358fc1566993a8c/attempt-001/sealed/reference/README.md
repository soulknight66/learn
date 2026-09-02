# Sealed reference implementation

This validator-only directory contains an independent C11 implementation of
the Pebble interpreter and x86-64 compiler.

```bash
make -C sealed/reference
sealed/reference/pebble eval starter/examples/count.pb
sealed/reference/pebble compile starter/examples/count.pb -o /tmp/count.s
cc /tmp/count.s -o /tmp/count
/tmp/count
```

The implementation parses once into a location-bearing AST, resolves names
before either backend, checks interpreter arithmetic, emits corresponding x86
overflow branches, uses a deterministic loop budget, and atomically renames a
completed assembly file. It is an educational reference, not a production
sandbox.
