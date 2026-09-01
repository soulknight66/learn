# Benchmarking plan

No benchmark was run and this repository claims no performance result or `BENCHMARKED` status.

If benchmarking is appropriate, compare the injected no-op backend and the real `unshare` backend so
planning/storage cost is not confused with kernel setup. Measure at least specification validation,
rootfs command resolution, initial state creation, one transition, full fake-backend execution, and
full real-backend execution. Include success, target nonzero exit, and setup failure paths.

Use a pinned machine or VM image, Python version, kernel, util-linux version, filesystem, rootfs tree,
CPU allocation, and privilege configuration. Warm caches explicitly or label cold and warm samples.
Report sample count, distribution (median and tail percentiles), uncertainty, and raw observations;
do not report only the fastest sample. Record output sizes and state-directory growth.

For contention studies, use separate processes and test distinct versus identical container IDs.
Verify correctness after each run: a fast corrupt state file is not a valid result. Real-backend runs
must also verify namespace behavior and cleanup. Keep benchmark artifacts out of learner-visible
claims until independently reproduced.

