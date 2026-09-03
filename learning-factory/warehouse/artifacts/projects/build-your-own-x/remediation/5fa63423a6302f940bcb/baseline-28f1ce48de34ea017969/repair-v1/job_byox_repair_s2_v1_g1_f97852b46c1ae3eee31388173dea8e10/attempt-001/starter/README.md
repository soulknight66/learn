# Starter implementation

The starter fixes the public data model and compiles to a placeholder `minish`. TODO markers identify the implementation boundary. Begin with `src/lexer.c`, then `src/parser.c`, then process execution and the loop.

Build with:

```sh
make -C starter
```

Run public tests against this directory with:

```sh
public_tests/run.sh starter
```

The untouched starter intentionally returns “not implemented,” so an initial failing test run is expected. Keep the signatures and ownership promises in `include/minish.h`; tests may link directly to them.
