# Benchmark harness

No benchmark label or performance number is claimed. run.py is an opt-in subprocess smoke benchmark
that emits raw CSV rows for three deterministic programs. It measures process startup, compilation,
and execution together, so it must not be described as VM-only throughput.

    PEBBLE_BIN=sealed/reference/build/pebble python3 benchmarks/run.py

The default is five samples per case. The harness verifies exit status and discards language output
before printing elapsed nanoseconds. Results intentionally are not checked into this repository.
