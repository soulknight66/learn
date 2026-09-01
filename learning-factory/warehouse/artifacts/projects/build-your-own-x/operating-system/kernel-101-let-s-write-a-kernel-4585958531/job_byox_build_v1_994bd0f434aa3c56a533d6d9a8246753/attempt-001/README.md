# TinyKernel State Lab

Build the deterministic core of a small 32-bit teaching kernel in C. The supplied boot path can
produce a freestanding x86 ELF image, while the same subsystem code is exercised as ordinary host
C so that mistakes are visible without an emulator.

This is an independently written challenge inspired by the broad topic in the catalog entry
“Kernel 101 – Let’s write a Kernel.” The linked article is provenance only; none of its text or
code is reproduced here.

## What you implement

Work in `starter/src/` and complete four stages in order:

1. A fixed-size physical-frame allocator.
2. A process table and deterministic round-robin scheduler.
3. Virtual-page mappings backed by the frame allocator.
4. A bounded RAM filesystem with explicit create/read/write/unlink operations.

The exact contract is in `REQUIREMENTS.md`; supporting explanations are in `CONCEPTS.md`.
Public tests expose one stage at a time:

```sh
make -C public_tests stage1
make -C public_tests stage2
make -C public_tests stage3
make -C public_tests stage4
make -C public_tests test
```

Build the freestanding image with:

```sh
make -C starter kernel
python3 environment/check_elf.py starter/build/tinykernel.elf
```

The result is an ELF kernel, not a host executable. If `qemu-system-i386` is installed, it may be
loaded by a Multiboot-compatible bootloader; constructing boot media is deliberately environment
specific and outside the scored contract.

## Progressive reveal

Read only as far as needed:

- Start with `starter/README.md` and stage 1 of `REQUIREMENTS.md`.
- Consult the matching section of `CONCEPTS.md` after your first attempt.
- Use `DESIGN_QUESTIONS.md` to reason about invariants before moving to the next subsystem.
- Run the complete public suite only after all four individual stages pass.

The reference implementation and deeper tests are sealed for independent evaluation. Passing the
public suite is useful evidence, but independent validation remains required.

## Safety boundary

This kernel is a teaching artifact. It has fixed limits, no hardware discovery, no interrupt
controller, no user mode, no persistent disk format, and no security claim. Do not deploy it or
boot it on a machine containing important data.
