# Starter workspace

The architecture shell links, but core functions in `src/terminal.c`, `src/keyboard.c`, and
`src/interrupts.c` contain `TODO(student)` markers. Start with host tests; a linked kernel is not yet
a working kernel.

```sh
make test       # public behavior checks; initially fails
make kernel     # freestanding ELF compile/link check
make inspect    # ELF class, entry point, sections, and first-byte dump
```

Keep pure logic independent of port I/O. The host suite compiles only `terminal.c` and `keyboard.c`.
The ISR path is exercised by sealed/static review because this host cannot inject an actual IRQ.

Expected end-state artifacts under this directory are generated into `build/` and can be removed
with `make clean`.
