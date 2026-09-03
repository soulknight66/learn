# CairnOS: build a small deterministic kernel core

CairnOS is a from-scratch C challenge about three pieces of an operating system that must agree:
a round-robin process scheduler, per-process virtual mappings backed by exclusive physical frames,
and a fixed-capacity in-memory filesystem with per-process descriptors. The same freestanding core
can be exercised as a normal host program or linked into a tiny Multiboot-compatible x86 kernel.

This is not a production OS. It deliberately replaces interrupts, hardware page tables, persistent
storage, and user-mode transitions with inspectable fixed-size state. That makes core invariants
testable before introducing hardware nondeterminism.

## Suggested progression

1. Read `CONCEPTS.md`, `REQUIREMENTS.md`, and `DESIGN_QUESTIONS.md`.
2. Implement the TODOs in `starter/src/cairn.c`; keep the public header unchanged.
3. Build with `make -C starter` and run `make -C public_tests run`.
4. Add your own boundary and state-machine tests.
5. Build the freestanding target with `make -C starter kernel` and inspect the ELF as described in
   `environment/README.md`.
6. Only after finishing, compare your work with the progressively sealed materials.

The public suite is intentionally incomplete. In particular, expect independent tests to corrupt
copies of state, fill every fixed table, preserve output parameters on errors, and exercise cleanup
across subsystem boundaries.

## Repository map

- `starter/`: learner-owned API skeleton, host demo, and bare-metal entry code
- `public_tests/`: visible contract examples
- `environment/`: exact tool locations and reproducible commands
- `sealed/reference/`: complete implementation and bootable reference
- `sealed/reference_tests/`: extended, adversarial, and benchmark drivers
- `debugging/`, `review_exercises/`, `adversarial/`, `benchmarks/`: staged prompts and policies

See `LICENSE_BOUNDARY.md` and `PROVENANCE.json` for the strict source boundary. Validation observations
are in `VALIDATION.md`; the permanent status remains `GENERATED` + `PARTIAL` pending independent
validation.
