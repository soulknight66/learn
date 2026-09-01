# Raspberry Pi 3 serial boot probe (partial)

This freestanding AArch64 probe is an independently written target adapter experiment. It enters on core 0, establishes a stack, and writes a fixed banner through PL011, assuming firmware has already configured that UART. It does not run the PebbleOS model or configure the MMU, exceptions, GPIO, clocks, or timer.

Expected build command:

```sh
make -C sealed/reference/pi3 clean all
```

It requires `aarch64-none-elf-gcc` and `aarch64-none-elf-objcopy`. Neither the toolchain nor Raspberry Pi hardware/QEMU was available in the recorded environment, so no image or boot result is claimed. The hard-coded Pi 3 peripheral base is not portable to all Pi models.
