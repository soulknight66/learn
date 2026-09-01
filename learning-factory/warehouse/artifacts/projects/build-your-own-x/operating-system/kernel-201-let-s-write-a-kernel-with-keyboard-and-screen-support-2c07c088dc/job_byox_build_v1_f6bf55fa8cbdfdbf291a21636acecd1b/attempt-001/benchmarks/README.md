# Benchmark plan

No benchmark result or `BENCHMARKED` label is claimed. Timing a hosted decoder would not establish IRQ
latency, and this generation host has no emulator.

A meaningful later benchmark should record toolchain/commit, emulator or CPU, clock source, warm-up,
sample count, input distribution, optimization flags, and raw samples. Measure separately:

- pure decoder cycles per byte for printable, modifier, prefix, and unsupported streams;
- worst-case terminal scroll time at the configured geometry;
- ISR entry-to-EOI latency without rendering; and
- sustained event rate and queue drops while foreground work is varied.

Correctness and boundedness come first. Do not optimize by moving scrolling into IRQ context or by
silently overwriting queued input.
