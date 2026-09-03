# Reproducible environment

The factory exposes a read-only GCC installation at:

```text
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

The tests use Python from:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
```

Neither path is assumed to be on `PATH`.  Both Makefiles prefer the exact GCC
path when present and still allow an explicit `CC=...` override.  The public
runner similarly accepts `PYTHON_BIN=...`.

Run `environment/check.sh` to print observed tool versions and compile a tiny
C17 translation unit from standard input with `-fsyntax-only`.  It does not
create scratch files or modify the source tree.
