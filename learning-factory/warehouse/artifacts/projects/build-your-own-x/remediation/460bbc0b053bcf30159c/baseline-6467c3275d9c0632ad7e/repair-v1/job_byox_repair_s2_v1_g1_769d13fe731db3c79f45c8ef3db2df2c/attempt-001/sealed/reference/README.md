# Sealed reference implementation

This directory contains a complete independent implementation of the CairnOS contract. Reveal it
only after attempting the starter. `src/cairn.c` is freestanding and shared by the host demo and the
32-bit Multiboot kernel.

Build from the repository root:

```sh
make -C sealed/reference clean all
./sealed/reference/build/demo
```

The bare-metal adapter in `boot/` checks scheduling, mapping, file I/O, cleanup, and invariants before
printing a serial result. The emulator command and unusual expected exit status are documented in
`../../environment/README.md`.

The implementation uses fixed arrays and performs every fallible check before its first write. It is
a reference for the challenge contract, not a claim of production OS completeness.
