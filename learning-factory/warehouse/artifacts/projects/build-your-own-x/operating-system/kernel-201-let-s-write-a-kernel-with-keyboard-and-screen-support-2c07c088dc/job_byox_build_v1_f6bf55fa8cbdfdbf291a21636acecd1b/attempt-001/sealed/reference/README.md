# Reference implementation

This directory is reveal-on-demand solution material. It contains one independently authored
implementation of the specified terminal, keyboard decoder, SPSC queue, legacy PIC/IDT hookup, and
foreground echo loop.

It is intentionally small, not production-ready. In particular it assumes Multiboot-provided
32-bit protected mode with a flat kernel code selector at `0x08`, legacy VGA text memory, a legacy
8042-compatible keyboard path, one CPU, and no firmware/device discovery.

Validation commands are:

```sh
make -C sealed/reference test
make -C sealed/reference kernel
python3 environment/verify_kernel.py sealed/reference/build/kernel.elf
```

An emulator boot is a separate evidence level.
