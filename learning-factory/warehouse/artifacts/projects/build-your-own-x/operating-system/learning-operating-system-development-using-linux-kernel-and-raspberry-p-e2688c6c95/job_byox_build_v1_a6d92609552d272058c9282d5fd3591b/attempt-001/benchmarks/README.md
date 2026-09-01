# Benchmark status

No benchmark was run and no performance numbers are claimed. The fixed limits are too small for throughput results to generalize to a real kernel, and this host model does not exercise exception entry, context switching, an MMU, caches, storage, or Raspberry Pi devices.

If benchmarking is added later, record compiler identity and flags, CPU/board identity, warm-up policy, iteration count, raw samples, and the exact revision. Separate at least process selection, mapped-page transfer, COW split, file transfer, and invariant-check costs. Do not compare host-model nanoseconds with real-hardware kernel operations as if they measure the same work.
