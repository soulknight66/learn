# Benchmark

The validator first builds each implementation with the recorded compiler and flags. `run.py`
then executes an identical 80,000-operation throughput workload and a deterministic mixed-size
fragmentation workload, preserving each implementation's raw JSON plus machine/toolchain
context in `results/smoke.json`. Generation never creates that result. Re-run repeatedly and
add profiling before interpreting small differences.
