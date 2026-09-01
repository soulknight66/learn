# Caller-Owned-Arena C Allocator Challenge

Build an allocator over a fixed byte arena supplied by the caller. This keeps metadata,
alignment, overflow, splitting, coalescing, `realloc` preservation, fragmentation, and
corruption detection visible without interposing on the process's libc allocator.

The portable C11 contract deliberately uses disjoint storage returned by `malloc` or
`aligned_alloc` (or equivalent storage with no incompatible declared object type). Merely
aligning and casting a declared `unsigned char[]` does not create `state` or `block` objects;
such stack/static arenas are outside this reference's portable effective-type contract.
Supporting them portably is a worthwhile representation-design extension, documented in the
sealed tradeoffs, rather than something these validators pretend to detect at runtime.

Start with `REQUIREMENTS.md`, `DESIGN_QUESTIONS.md`, `include/allocator.h`, `starter/`, and
`public_tests/`. Do not expose `sealed/` to a learner workspace. When ready, reveal an
address-ordered first-fit reference and compare it with best-fit and segregated-size-bin
implementations through the same C API, strict compiler flags, contracts, deterministic
model workload, and benchmark.

Factory validation runs `python3 scripts/build_all.py`, executes every architecture's
public/withheld/model checks, gates sanitizers on a compile-and-execute probe, reproduces one
metadata-corruption bug, demonstrates a review finding, and only then generates actual raw
benchmark evidence. `benchmarks/results/smoke.json` deliberately does not exist at generation
time.

This is a bounded educational allocator, not a `malloc` replacement and not production
ready. Passing evidence can support `BUILDS`, `TESTED`, `BENCHMARKED`, and
`REVIEWED`, always with `PARTIAL`; it cannot support `PRODUCTIONIZED`.
