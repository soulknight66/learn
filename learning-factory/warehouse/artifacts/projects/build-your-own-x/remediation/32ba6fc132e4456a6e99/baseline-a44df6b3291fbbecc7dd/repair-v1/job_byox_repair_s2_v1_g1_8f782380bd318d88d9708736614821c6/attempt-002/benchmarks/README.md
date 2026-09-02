# Benchmark status

No benchmark was executed and no throughput, latency, allocation, or durability
number is claimed. This support directory is outside the learner-visible
allowlist. A small manual harness is stored under `sealed/benchmarks/` to keep
implementation-bearing evaluation material sealed.

The harness measures one local append/reopen/read scenario only. It is not a
substitute for warmup control, forked JVMs, latency distributions, forced-write
comparisons, fault injection, or a production capacity study. The artifact
must not receive a `BENCHMARKED` label based on the harness's existence.
