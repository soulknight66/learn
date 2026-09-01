# Sealed reference tests

`test_reference.c` is a deterministic hosted test program for the sealed implementation. Run it through:

```sh
make -C sealed/reference test
```

It covers:

- all fixed constants and numeric status values;
- arbitrary-byte initialization and null argument handling;
- scheduler capacity, stable round-robin order, READY/RUNNING blocking, all live exit paths, reaping, PID collision avoidance, unchanged error outputs, and the one-RUNNING invariant;
- VM lowest-frame allocation, frame exhaustion, address boundaries, page isolation, read-only enforcement, zero-filled allocation and reuse, unmap behavior, unchanged failed operations, and corrupt frame metadata detection;
- RAMFS name validation, exact/case-sensitive lookup, file exhaustion and reuse, binary partial reads, EOF rules, sparse writes, non-truncating overwrite, the exact 128-byte boundary, atomic range failures, zero-length calls, aliased write input, and released-data clearing.

The test uses the hosted library (`stdio.h` and `string.h`) only in the test executable. Those dependencies do not enter the freestanding core archive.

This suite is sealed because it reveals edge cases and expected transitions. A passing local run is not a promotion label and is not a substitute for the worker-controlled independent validator.
