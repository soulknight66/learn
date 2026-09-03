# Starter

Implement `src/cairn.c` against the unchanged contract in `../REQUIREMENTS.md`. The skeleton is
deliberately compilable but returns `CAIRN_ERR_UNIMPLEMENTED` from unfinished operations.

Commands:

```sh
make -C starter
make -C public_tests run
make -C starter kernel
```

The first command builds a hosted demo and the freestanding ELF. The public test command is expected
to fail until the TODOs are complete. The ELF target proves linkability; the starter boot shim only
prints a diagnostic and halts, so it is not evidence that your implementation is correct.

Do not add host-only calls to `src/cairn.c`. If you want logging, keep it in `src/demo.c` or the boot
adapter.
