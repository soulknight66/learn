# Keystroke Kernel Lab

Build the smallest useful input/output edge of a 32-bit x86 kernel: a text terminal backed by VGA
cells, a stateful PS/2 Set-1 keyboard decoder, and an interrupt-to-main-loop event queue. The logic is
designed to run both as freestanding C and under ordinary host tests, so most mistakes can be found
without debugging a virtual machine.

This is a challenge, not a tutorial transcript. Its behavior is defined by [REQUIREMENTS.md](REQUIREMENTS.md),
and the incomplete implementation lives in `starter/`.

## Suggested progression

1. Implement terminal initialization, control characters, wrapping, and scrolling.
2. Decode Set-1 make/break bytes, modifiers, Caps Lock, and selected `0xE0` keys.
3. Implement the bounded single-producer/single-consumer event queue.
4. Pass the public host tests.
5. Build `kernel.elf`, inspect its multiboot header, then boot it in an emulator you trust.
6. Answer the design questions before revealing sealed discussion material.

## Quick start

```sh
make -C starter test
make -C starter kernel
```

The first command is expected to fail until the TODOs are implemented. `kernel` needs GCC capable
of emitting 32-bit freestanding objects and GNU `ld` with `elf_i386` support. Emulator execution is
optional and intentionally separate from the deterministic host tests; see `environment/README.md`.

## Scope and safety

The deliverable supports screen output and keyboard input only. It does **not** implement processes,
virtual memory, filesystems, user mode, USB keyboards, Unicode, or production-grade hardware
discovery. Those catalog concepts are placed in context in `CONCEPTS.md`, not falsely claimed as
features. Run kernel code only in an emulator or disposable lab machine.

The top-level manifest remains `GENERATED` + `PARTIAL`. Independent validation is required even if
local commands pass.
