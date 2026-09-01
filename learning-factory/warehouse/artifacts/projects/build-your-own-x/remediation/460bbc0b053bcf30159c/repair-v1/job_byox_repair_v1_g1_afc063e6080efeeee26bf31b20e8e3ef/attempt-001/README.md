# MicaOS Core Lab

MicaOS Core Lab is a small C11 exercise in building deterministic, bounded kernel-like services. You will complete three independent in-memory models:

- a scheduler for at most 8 processes;
- a virtual-memory model with 16 virtual pages, 8 physical frames, and 64-byte pages; and
- a flat RAM filesystem with at most 8 files and 128 bytes per file.

This is a **model core**, not a bootable or production operating system. It does not boot, enter a privileged CPU mode, handle interrupts, drive hardware, provide isolation from host processes, or persist data across runs. The model exists so that state transitions, capacity limits, protection checks, and failure behavior can be tested precisely on the host.

## Where to start

The declarations, types, and status values in the public starter headers are the authority for API shape. [REQUIREMENTS.md](REQUIREMENTS.md) defines the observable behavior. Do not change a public declaration merely to make an implementation more convenient.

Build and run the public checks from the repository root:

```bash
make -C starter build
make -C starter test
```

The public tests are useful feedback, but they are not the full specification. Final validation also exercises the documented boundary and failure cases. A passing implementation therefore needs to satisfy the contracts, not only the examples visible in the test sources.

## Suggested milestones

Work through one milestone at a time. Each milestone reveals only the next useful set of questions; [DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md) is available when you want broader review prompts.

1. **Establish the empty states.** Read the headers and constants, build the starter, and make every initializer produce a deterministic empty object.
2. **Complete process lifecycles.** Implement spawn, schedule, block, wake, exit, and reap. Check the 8-process boundary and all invalid transitions before moving on.
3. **Complete page lifecycles.** Implement map, unmap, read, and write. Check exhaustion, read-only mappings, and zeroed remapping.
4. **Complete file lifecycles.** Implement create, offset-based write and read, and unlink. Check name validation, sparse-gap zeroing, the 8-file limit, and atomic rejection of data beyond 128 bytes.
5. **Harden the boundaries.** Re-read the requirements for null or invalid inputs, one-past-the-limit values, repeated operations, and state preservation after failure. Run the complete public suite again.

## Constraints worth keeping visible

- Use C11 and keep the core friendly to a freestanding environment.
- Use the fixed capacities exposed by the starter; do not turn a bounded model into an unbounded one.
- Keep behavior deterministic. The same initial state and operation sequence must produce the same results.
- Do not rely on QEMU, NASM, networking, wall-clock timing, threads, or host filesystem persistence.
- Treat every rejected operation as part of the API contract. In particular, capacity failures must not leave partial state behind.

See [CONCEPTS.md](CONCEPTS.md) for the ideas the lab exercises and [environment/README.md](environment/README.md) for the available toolchain.
