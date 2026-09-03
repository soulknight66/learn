# Learner and automation guide

Work only in `starter/` for the learner implementation. Do not copy or inspect
sealed instructor material. Use the observable contract and public black-box
tests as the source of truth.

## Deterministic workflow

```sh
make -C starter clean
make -C starter CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
MSH_BIN="$PWD/starter/msh" \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 public_tests/test_shell.py
```

Keep builds warning-clean under the flags already in the Makefile. Add tests
for each behavior before changing process management. Do not add network
dependencies, generated binaries, credentials, or symlinks. Subprocesses must
use `fork`/`exec`-style argv execution, not delegate parsing to `system(3)` or
`/bin/sh -c`.

For job-control tests, use a pseudo-terminal rather than assuming ordinary
captured stdin is a terminal. Tests must use bounded timeouts and clean up
process groups they create.
