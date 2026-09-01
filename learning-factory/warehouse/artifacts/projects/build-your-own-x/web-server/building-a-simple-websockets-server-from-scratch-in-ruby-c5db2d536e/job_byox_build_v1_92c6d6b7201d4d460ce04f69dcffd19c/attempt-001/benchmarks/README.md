# Benchmark plan (not executed)

No benchmark numbers are claimed. TCP loopback binding is blocked in the build
sandbox, and a UNIX socket microbenchmark would not justify network-service
throughput conclusions.

On a suitable isolated host, measure at least:

- handshake latency and throughput at 1, 8, 32, and saturated clients;
- echo throughput for 16 B, 1 KiB, 64 KiB, and maximum messages;
- fragmented versus single-frame messages;
- memory and thread count under idle, slow-header, and slow-frame clients;
- admission behavior above `max_clients`; and
- shutdown duration with idle reads and blocked callbacks.

Record Ruby version, operating system, CPU allocation, exact command, sample
count, warmup, percentile method, error count, configuration limits, and raw
results. Use a separate client process, monotonic clocks, bounded runs, and
payload verification. Do not promote `BENCHMARKED` until an independent harness
reproduces recorded results.

