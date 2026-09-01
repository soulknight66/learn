# Adversarial validation

The model fuzzer uses a fixed seed and compares every operation with a Python dictionary. The
stress test gives each thread disjoint keys so the final state is deterministic. Fault injection
appends a torn envelope and checks both recovery and a later compaction. These are bounded smoke
workloads; increase counts and add filesystem/process crash injection for deeper campaigns.
