# Lab Environment

The workspace provides a host C toolchain suitable for building and testing the MicaOS model core. Available tools include `cc`, `gcc`, `make`, `ld`, and `objcopy`.

From the repository root, use the supported targets:

```bash
make -C starter build
make -C starter test
```

Run `build` after interface or implementation changes and `test` before claiming completion. The build rules select the intended sources and flags; invoking individual compiler commands is useful for diagnosis but is not a substitute for the supported targets.

QEMU and NASM are not installed. They are not needed: this lab builds a host-tested C11 model, not a bootable disk or kernel image. Do not add an emulator, assembly boot path, package download, or network dependency to solve the exercise.

The core should remain freestanding-friendly even though its public tests execute as normal host programs. Avoid making core behavior depend on host files, environment variables, clocks, processes, threads, locale, or terminal I/O. Test diagnostics may use the host facilities already provided by the starter harness.
