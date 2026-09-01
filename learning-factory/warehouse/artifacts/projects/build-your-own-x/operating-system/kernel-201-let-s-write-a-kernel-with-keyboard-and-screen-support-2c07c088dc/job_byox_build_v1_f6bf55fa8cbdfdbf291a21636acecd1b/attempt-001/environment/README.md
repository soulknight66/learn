# Environment

## Deterministic host layer

Required:

- a C11 host compiler (`gcc` is used by the supplied Makefiles),
- GNU Make,
- Python 3 for the ELF/header verifier,
- GNU binutils with an `elf_i386` linker target.

Check availability without changing the machine:

```sh
sh environment/check_tools.sh
```

Audit the required/forbidden structure, immutable metadata objects, regular-file boundary, and
credential-shaped text with:

```sh
python3 environment/audit_artifact.py
```

The freestanding build uses `gcc -m32` only to emit objects; it does not need 32-bit libc. Run:

```sh
make -C starter kernel
python3 environment/verify_kernel.py starter/build/kernel.elf
```

## Optional boot layer

`qemu-system-i386` is optional and was not available in the generation host. If installed locally,
an example invocation is:

```sh
sh environment/run_qemu.sh starter/build/kernel.elf
```

Use the emulator's text display, click/focus it before typing, and quit with its documented escape
sequence. This repository does not automate keystrokes or claim a boot result. A GRUB ISO workflow
would additionally need GRUB utilities and an ISO builder; none are vendored.

Do not boot unfinished code on a physical computer. Tool presence, successful compilation, valid
header arithmetic, emulator boot, and hardware compatibility are distinct evidence levels.
