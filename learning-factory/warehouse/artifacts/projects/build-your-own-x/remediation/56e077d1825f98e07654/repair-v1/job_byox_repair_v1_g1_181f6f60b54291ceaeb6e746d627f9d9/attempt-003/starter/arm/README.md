# Optional ARMv7-A port scaffold

Target: QEMU `virt`, AArch32, PL011 UART, raw kernel loaded at `0x40010000`.

Complete `start.S` and `kernel_main.c`, then add a context-switch routine that follows AAPCS. The
portable host tests do not compile this directory. The Makefile deliberately fails early when the
cross compiler is absent.

This scaffold contains no working context-switch implementation.
