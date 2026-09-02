# Starter kernel

This tree is intentionally incomplete but cross-buildable. Search for `Stage`
comments and implement in dependency order:

1. `kernel/uart.c` for the first serial observation.
2. `kernel/scheduler.c`, `kernel/runtime.c`, and `arch/arm/context.S` for tasks.
3. `kernel/vm.c` and `arch/arm/mmu.c` for memory management.
4. `kernel/ramfs.c`, then integrate all markers in `kernel/main.c`.

The reset file and linker script establish a minimal C environment. You may
modify them, but preserve the link address and `.bss`/stack contracts. Public
tests compile only the portable scheduler, VM, and RAMFS units; an implementation
can pass those tests and still fail on ARM.

No hosted functions are available in the kernel. Prefer short internal loops
over inventing partial libc APIs, and validate inputs before modifying tables.
