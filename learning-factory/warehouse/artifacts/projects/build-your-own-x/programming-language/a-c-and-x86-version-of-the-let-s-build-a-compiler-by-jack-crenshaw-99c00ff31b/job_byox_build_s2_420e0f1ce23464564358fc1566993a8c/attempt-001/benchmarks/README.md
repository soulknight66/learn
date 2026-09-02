# Optional benchmark harness

`run_benchmark.py` measures end-to-end process time for the interpreter and for
an already linked generated executable on a deterministic summation program.
It validates output before timing and emits JSON to standard output.

```bash
python3 benchmarks/run_benchmark.py \
  --binary sealed/reference/pebble --iterations 100000 --repetitions 5
```

Process startup is included; compilation time is not. Results depend on the
machine, load, compiler, and libc. No benchmark result is stored in this
artifact, no performance threshold is asserted, and the manifest does not
claim `BENCHMARKED`.
