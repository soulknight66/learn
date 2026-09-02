# Benchmark protocol (not executed)

No benchmark label or numeric result is claimed. Timing on the shared generation host would not be
transferable evidence.

A future evaluator may measure, in a disposable workspace:

1. import latency and peak disk use over fixed tar corpora at 1, 10, and 100 MiB expanded size;
2. snapshot creation latency for many small files versus fewer large files;
3. SQLite claim throughput and lock latency at 1, 2, 8, and 32 independent processes;
4. runner launch overhead and log-write disk growth at fixed byte rates; and
5. cleanup/reconciliation time after injected crash points.

Record the exact corpus digests, interpreter path/version, filesystem type, mount options, CPU model,
warmup policy, sample count, raw samples, summary method, and whether caches were warm. Enforce outer
timeouts and disk quotas. Never infer isolation security from throughput numbers.
