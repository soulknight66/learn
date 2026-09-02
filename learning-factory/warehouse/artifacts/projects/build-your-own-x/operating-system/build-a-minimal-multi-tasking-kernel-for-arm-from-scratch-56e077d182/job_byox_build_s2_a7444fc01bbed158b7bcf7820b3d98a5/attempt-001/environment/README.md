# Reproducible environment

## Target contract

| Item | Value |
|---|---|
| Board | QEMU `versatilepb` |
| CPU | ARM926EJ-S (`-cpu arm926`) |
| RAM | 128 MiB |
| ELF load/link address | `0x00010000` |
| UART | PL011 at `0x101f1000` |
| UART data register | base + `0x00` |
| UART flag register | base + `0x18`, TX-full bit 5 |
| Translation format | ARMv5 short descriptors |
| Kernel mode | 32-bit ARM, supervisor, little-endian |

The factory provides these read-only binaries; they are intentionally absent
from `PATH`:

```text
/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc
/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-objcopy
/arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld
/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64
```

## Cross-build

```sh
make -C starter clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

## Bounded emulation

Use a timeout so a bad exception vector or scheduler cannot stall automation:

```sh
/usr/bin/timeout 10s \
  /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  -M versatilepb -cpu arm926 -m 128M -nographic -monitor none \
  -semihosting-config enable=on,target=native \
  -kernel starter/build/kernel.elf
```

Semihosting is used only to let a completed educational run terminate QEMU. It
is not used for UART, scheduling, memory, or filesystem behavior. A candidate
that does not issue the exit request will normally be stopped by the timeout;
inspect ordered serial markers rather than treating timeout alone as a failure.

No upstream checkout, package download, privileged device, disk image, or
network service is needed.

For the isolated host GCC, pass
`-B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/` so it can find its linker. Its
sanitizer executables also need the GCC `lib64` directory at runtime. The exact
validated invocation, including the sandbox-specific LeakSanitizer setting, is
recorded in `VALIDATION.md`.
