# Starter workspace

`include/pebble.h` is the fixed public contract. `src/pebble.c` is a compiling scaffold: initialization and a few read-only checks are present, while state-changing operations intentionally return `PEBBLE_ERR_NOT_IMPLEMENTED`.

Recommended sequence:

1. Make the process tests pass without touching virtual memory or files.
2. Implement map/unmap and single-page transfer, then generalize carefully to cross-page ranges.
3. Add fork and copy-on-write only after ordinary frame ownership is stable.
4. Add filesystem operations with failure rollback.
5. Implement the full invariant checker last, then call it frequently while debugging.

Commands, run from the repository root:

```sh
make -C starter clean all
make -C starter public
```

`make` creates files only under `starter/build/`. Do not change constants or function signatures to make a test easier. Public tests are examples, not a complete specification; `REQUIREMENTS.md` is authoritative.
