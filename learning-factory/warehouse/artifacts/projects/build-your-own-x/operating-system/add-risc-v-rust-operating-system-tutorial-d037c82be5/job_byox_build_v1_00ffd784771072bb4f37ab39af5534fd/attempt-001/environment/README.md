# Environment

The project needs a stable Rust toolchain (Rust 1.74 or newer is the stated
baseline) and Python 3.6+ for the structural checker. It has no crates.io,
network, nightly, QEMU, firmware, linker-script, or RISC-V target dependency.

From the repository root:

```bash
python3 environment/check_structure.py
python3 environment/run_public.py
```

The second command invokes Cargo with an argv array, offline mode, a 120-second
timeout, captured exit status, and the manifest in `public_tests/`. It exits 2
with a reproducible `BLOCKED` message if Cargo is absent. Cargo itself writes
normal scratch build products under `public_tests/target/`; those products are
not provenance artifacts and may be removed explicitly.

This is a host-side semantic model. QEMU and a RISC-V cross target are neither
needed nor sufficient to claim that it boots.
