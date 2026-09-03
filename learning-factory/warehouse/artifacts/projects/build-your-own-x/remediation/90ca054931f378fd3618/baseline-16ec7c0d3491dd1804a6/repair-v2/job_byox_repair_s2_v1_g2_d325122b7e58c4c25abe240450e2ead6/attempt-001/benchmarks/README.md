# Benchmark design (no performance claim)

No benchmark label or timing result is claimed.  If measuring locally, separate
compile time from VM execution and include workloads dominated by arithmetic,
branches, heap access, and guest dispatch.  Record exact binary hashes, compiler
version, flags, host, repetitions, warm-up policy, and raw samples.

Do not compare the starter stub with the sealed reference as though it were a
performance competition.  Correctness, resource ceilings, and identical output
must be independently verified before timing.
