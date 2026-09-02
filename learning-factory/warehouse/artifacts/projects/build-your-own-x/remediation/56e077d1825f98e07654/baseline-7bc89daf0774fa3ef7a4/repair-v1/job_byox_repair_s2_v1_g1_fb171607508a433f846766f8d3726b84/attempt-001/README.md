# Build a minimal multi-tasking ARM kernel

This challenge starts at reset and ends with a small kernel that can run several
cooperatively scheduled tasks, maintain per-process virtual-address mappings,
and store files in a bounded RAM filesystem. The target is the ARM926EJ-S CPU on
QEMU's `versatilepb` board. There is no C library, allocator, firmware, or host
operating-system service beneath the kernel.

The project is independently written from the catalog topic. The linked upstream
resource is provenance only; its code and prose are not part of this pack.

## What you build

Work in `starter/` and implement the contracts in its headers. Progress in four
observable stages:

1. Boot the freestanding ELF and write `LF-KERNEL boot` through the PL011 UART.
2. Make scheduler state transitions deterministic and connect them to the
   supplied ARM context-switch boundary.
3. implement frame allocation, address-space mappings, and ARM MMU setup.
4. Implement the fixed-capacity RAM filesystem and demonstrate the three
   subsystems together in one emulated boot.

The required behavior and edge cases are in `REQUIREMENTS.md`. `CONCEPTS.md`
explains the relevant mechanisms without giving implementations, and
`DESIGN_QUESTIONS.md` supplies checkpoints for a design review.

## Feedback loop

The portable public tests need only a C11 host compiler:

```sh
make -C public_tests clean test
```

The untouched starter intentionally fails behavioral tests. A failing test is
useful evidence until the corresponding stage is implemented.

To cross-build, pass an ARM bare-metal tool prefix explicitly because the
factory toolchain is not added to `PATH`:

```sh
make -C starter CROSS_COMPILE=/absolute/path/to/arm-none-eabi-
```

To boot the result (QEMU command shown schematically):

```sh
qemu-system-arm -M versatilepb -cpu arm926 -m 128M -nographic \
  -monitor none -kernel starter/build/kernel.elf
```

See `environment/README.md` for the precise board contract and reproducible
commands. The project has no network or upstream checkout requirement.

## Completion signal

A candidate implementation is complete only when:

- public tests pass without changing their assertions;
- a freestanding ELF builds with no undefined symbols;
- QEMU prints the ordered markers required in `REQUIREMENTS.md`;
- the learner can justify failure atomicity, access checks, and scheduler
  invariants in a design review.

Those checks are necessary, not sufficient. `MANIFEST.yaml` deliberately
retains `GENERATED` and `PARTIAL`; independent harness validation is mandatory.
