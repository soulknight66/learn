# Benchmark plan (not executed as a performance claim)

No `BENCHMARKED` label or performance number is claimed. A useful future harness would measure host
nanoseconds per scheduler tick, single-page and eight-page copies, create/write/read/unlink cycles,
and full-filesystem failed replacements. Record compiler, flags, CPU, sample count, warmup, median,
tail percentiles, and raw samples.

For ARM, measure context-switch cycles with the architectural counter only after configuring its
access and accounting for UART perturbation. QEMU timing must be labeled emulator timing and must not
be presented as target-silicon performance.
