# Benchmark exercise answer key

A sound matrix changes one independent variable at a time. Payload size exposes
copy cost; result count exposes read snapshot cost; replica factor exposes
synchronous fan-out; backlog exposes recovery's total copied bytes; membership
size exposes election scanning. Use fresh state where growth would otherwise
confound trials.

Expected complexity, not measured performance:

- local append copies a payload and performs an amortized list append;
- replicated append copies proportional to payload bytes times current ISR
  members;
- a read costs proportional to records and bytes returned because values remain
  isolated;
- recovery costs proportional to missing records and their bytes; and
- sorted election scans configured replicas in the worst case.

Warm each parameter combination, use several independent JVM forks, consume a
checksum of returned data, and examine raw distributions rather than only an
average. Capture allocation and GC only when a real profiler is available.
Recovery setup and failure injection belong outside the timed interval unless the
benchmark explicitly measures the full incident.

Interpretation must preserve correctness. Removing array copies, reducing the
replicas acknowledged, or reading above the watermark changes semantics and
cannot be presented as a performance improvement.

No benchmark was executed during generation because the host lacked Java.
Accordingly this answer key contains no latency, throughput, allocation, or
profiler numbers.

