# Adversarial validation

Select the target explicitly with `KVSTORE_IMPL=reference` or
`KVSTORE_IMPL=production`; the latter name selects the instrumented teaching variant at its
stable archive path and does not imply production readiness.

The model fuzzer uses a fixed seed and compares every operation with a Python dictionary. The
stress test gives each thread disjoint keys so the final state is deterministic. Fault injection
appends a torn envelope and checks both recovery and a later compaction. These are bounded smoke
workloads; increase counts and add filesystem/process crash injection for deeper campaigns.
