# Sealed implementation review

The reference sources were reviewed against the published ABI and contract.
The strongest properties are bounded pointer/name scans, overflow-safe file
ranges, output clearing on error, preflight-before-mutation, full slot clearing
on reap/unlink, and a scheduler that selects before changing process state.

The hosted tests cover every public function, all declared error classes,
capacity edges, combined permissions, PID wrap, sparse gaps, and rejected-write
state equality. Fixed-seed sequence tests additionally check uniqueness and
ownership invariants after thousands of operations. The freestanding build
uses the same subsystem sources, preventing a hosted-only reference from
hiding C library calls.

Known limitations are intentional and material: no concurrency controls,
context switching, hardware page tables, frame allocator, directories,
persistence, crash recovery, or Raspberry Pi peripheral support. Public
structures can be externally corrupted, and functions generally assume they
receive a state previously produced by the API. The implementation has not
been fuzzed by an independently controlled engine, benchmarked, tested on
physical hardware, or assessed for production security.

Accordingly this review does not claim `REVIEWED`, `TESTED`, or
`PRODUCTIONIZED` validation labels. Only the independent worker harness may
make those promotions.
