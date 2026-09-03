# Reproducible environment

Configured read-only tools used by this artifact:

- C compiler: `/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc`
- sanitizer runtime: `/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64`
- assembler: `/arm/tools/nasm/nasm/2.16.03/rhe8-x86_64/bin/nasm`
- linker: `/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld`
- ELF inspection: `/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/readelf`
- emulator: `/arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386`
- emulator GLib runtime: `/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64`
- Python: `/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`

The Makefiles invoke tools by these exact paths and accept command-line overrides. QEMU in this
environment requires the listed `LD_LIBRARY_PATH`; without it, startup fails with a GLib symbol lookup
error. Sanitized tests likewise pin the GCC runtime path and disable LeakSanitizer because this
sandbox does not expose the process inspection it requires; AddressSanitizer and UndefinedBehaviorSanitizer
remain enabled.

Typical checks from the repository root:

```sh
make -C starter clean all
make -C public_tests clean run
make -C sealed/reference clean all
make -C sealed/reference_tests clean run
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/readelf -h sealed/reference/build/cairnos.elf
LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-i386 \
  -kernel sealed/reference/build/cairnos.elf -nographic -monitor none -serial stdio \
  -no-reboot -device isa-debug-exit,iobase=0xf4,iosize=0x04
```

The reference kernel reports `CAIRNOS: PASS` and asks the debug-exit device to stop QEMU. That device
encodes guest value `0x10` as host exit status 33, so status 33 is the expected success condition—not
a generic shell success status.
