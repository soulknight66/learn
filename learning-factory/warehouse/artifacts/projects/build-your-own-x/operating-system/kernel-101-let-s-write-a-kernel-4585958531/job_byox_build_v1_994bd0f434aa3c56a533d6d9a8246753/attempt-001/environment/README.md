# Build environment

Required for host validation:

- an ISO C11 compiler (`cc`),
- GNU-compatible `make`, and
- Python 3.6 or newer for the ELF checker.

Required for the freestanding artifact:

- GCC or a compatible compiler supporting `-m32` object generation, and
- GNU `ld` supporting `-m elf_i386`.

No third-party C libraries are used. A 32-bit host libc is not required because the kernel is
linked freestanding with `ld`; public tests are ordinary native executables.

QEMU and GRUB utilities are optional and were unavailable in the generation environment. Their
absence blocks an observed boot test, not host behavioral tests or ELF construction.
