# Starter guide

The public interface is in `include/tinykernel.h`. Complete the `TODO` functions in `src/frames.c`,
`src/scheduler.c`, `src/vm.c`, and `src/ramfs.c`; do not change signatures, constants, or public
structure layouts.

Suggested loop:

```sh
make host-check
make -C ../public_tests stage1
```

Then advance through stages 2–4. `make kernel` creates `build/tinykernel.elf`. The boot, linker, VGA
console, and integration files are supplied so that subsystem work stays focused. A starter kernel
may build even while it reports that the lab is incomplete; behavioral tests decide completion.

No dynamic allocation or libc is available in subsystem source. Small local helper functions are
welcome. Treat null pointers, invalid enum values, full tables, and repeated operations as ordinary
error paths.
