# Reproducible environment

The factory exposes a read-only GCC installation at:

```text
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

The tests use Python from:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3
```

GCC is bound to GNU Binutils at:

```text
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin
```

None of these paths is assumed to be on `PATH`.  All three Makefiles prefer the
exact GCC path and pass its linker-search `-B` option explicitly.  `CC=...` and
`BINUTILS_DIR=...` remain documented overrides; use `BINUTILS_DIR=` only when
the selected compiler can resolve its own tools.  The public runner similarly
accepts `PYTHON_BIN=...`.

Run `environment/check.sh` to print observed GCC, GNU ld, and Python versions,
confirm GCC's resolved linker path, and compile, link, and execute a tiny C17
program.  The script creates a uniquely named scratch directory beside itself
and removes it on exit.
