# Benchmark design exercise

This learner-visible file is a prompt, not a performance claim. Do not inspect
the sealed answer key.

Design a reproducible Java 17 benchmark for:

1. PartitionLog append across at least three payload sizes;
2. bounded reads across several result counts;
3. ReplicatedPartition append for replica factors 1, 3, and 5;
4. catch-up of different backlogs; and
5. leader failure/election with different membership sizes.

Separate setup from measurement. Generate payloads before timed sections, consume
returned offsets and bytes so work cannot be discarded, include warm-up and
multiple measured forks, and retain raw samples. Do not print per operation in a
timed loop.

Report source revision, JDK vendor/version, OS, CPU, memory, JVM flags, heap
settings, payload distribution, operation count, warm-up, fork count, and whether
GC or allocation profiling was enabled. Report throughput or time per operation
with median and tail percentiles; do not report more precision than the run
supports.

Explain how copying, replica count, read size, recovery backlog, allocation, GC,
and lock contention could affect results. Compare only runs with equivalent
semantics. A faster implementation that drops defensive copies or commitment
checks is incorrect, not an optimization.

If JMH is unavailable, create a clearly labeled coarse harness using System.nanoTime
with process forks and sufficiently long batches. State that such results are
more vulnerable to JVM optimization and harness bias. Do not invent measurements
when a JDK or profiler is unavailable.

