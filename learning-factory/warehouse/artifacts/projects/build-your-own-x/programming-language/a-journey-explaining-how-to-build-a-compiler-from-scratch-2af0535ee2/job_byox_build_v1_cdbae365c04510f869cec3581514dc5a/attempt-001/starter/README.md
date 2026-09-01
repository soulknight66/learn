# Starter

The public header and CLI plumbing are complete. `src/pebble.c` is an intentionally non-solution
placeholder: it returns a deterministic compile diagnostic so the project builds before you begin.
Replace its internal representation and implement all API functions without changing
`include/pebble.h`.

Suggested internal milestones are scanner, expression emitter, scoped names, statement/control-flow
emission, then VM hardening. Keep compile failure atomic: `*out_program` must stay null unless the
whole source compiled successfully.

```sh
make
make test
```

The initial `make` should succeed. The initial test run is expected to fail until the compiler is
implemented; that failure is not a host setup problem.
