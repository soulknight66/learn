# Reproducible benchmark harness

No benchmark label or performance number is claimed. `run_benchmark.py` is a bounded local harness for future comparisons; it reports raw per-run wall times and a median, includes warmups, validates exit status and output shape, and invokes the compiler without a shell.

```sh
python3 benchmarks/run_benchmark.py \
  --binary sealed/reference/build/sprig --iterations 7 --warmup 2
```

Wall time is sensitive to host load, compiler flags, CPU policy, and filesystem placement. Record those factors and the exact command before treating results as evidence. Do not compare runs from unlike hosts. The generated workload (60 bindings and 190 prints) stays within Sprig’s declared binding and instruction limits and measures compile-plus-execute, not either phase in isolation.
