# Benchmark status

No benchmark label is claimed. Controller timing on tiny temporary trees would say little about the
dominant real costs: rootfs size, filesystem copy/reflink behavior, cache state, storage hardware,
namespace setup, and workload startup.

A meaningful future benchmark must state hardware, kernel, filesystem and mount options, rootfs
manifest and byte/file counts, warm-up policy, cache treatment, repetitions, statistic, and variance.
It should separately measure create, metadata-only list/inspect, namespace startup, and delete.

No numbers were generated for this artifact, and no upstream performance claim is repeated.
