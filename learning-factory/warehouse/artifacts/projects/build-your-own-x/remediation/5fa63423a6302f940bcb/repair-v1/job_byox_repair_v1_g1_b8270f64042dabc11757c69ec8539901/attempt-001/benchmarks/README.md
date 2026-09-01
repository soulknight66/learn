# Benchmark harness

`run_bench.py` measures a few narrow costs of a built `byosh`. The repository
contains no benchmark results, and this harness does not confer the
`BENCHMARKED` label. Its runtime JSON calls every number an unvalidated local
measurement.

The harness is compatible with Python 3.6 and uses only the standard library.
Build the reference separately, then run from the repository root:

```sh
python3 benchmarks/run_bench.py \
  --shell ./sealed/reference/byosh \
  --warmups 3 \
  --iterations 20 \
  --output benchmark-local.json
```

The output path should remain a scratch artifact unless an independent
validator deliberately records it with machine/toolchain provenance.

## Workloads

- `cold_builtin` starts one shell and runs one redirected `pwd`.
- `cold_external` starts one shell and runs the `true` utility resolved from `PATH`.
- `cold_pipeline` starts one shell and passes one byte through a two-stage
  pipeline.
- `batch_builtins` starts one shell and reads 100 redirected builtins on stdin,
  exposing amortized parse/dispatch cost.
- `batch_quote_parse` starts one shell and reads 100 quote/escape-heavy external
  commands whose output is discarded.

Cold workloads intentionally include process startup. Batch workloads report
both invocation time and time divided by the declared operation count. They are
not interchangeable metrics.

## Measurement controls

The runner validates that the target is a regular executable and records its
SHA-256 digest. It resolves workload utilities from `PATH`, passes absolute
paths to the shell, and fails clearly if one is missing. Every sample uses a
fresh temporary working directory, captures stderr, discards normal command
output, enforces a per-sample timeout, and starts a new session. Cleanup uses a
separately bounded `ps --sid` helper to request only that session's rows and
terminate every member, including pipeline processes in groups distinct from
the shell, then reaps the shell with bounded waits. If the procps `--sid`
selector is unavailable, cleanup fails closed. Warmups are executed but excluded from
samples. Workloads run in rotating order to reduce systematic ordering bias.

Interpret short timings cautiously. CPU frequency changes, filesystem cache,
scheduler load, executable lookup, libc, kernel, and instrumentation can dominate
this small program. For publishable evidence, pin down the environment, run
multiple independent processes, retain raw samples, compare matching builds,
and report uncertainty rather than only the median. Use a profiler before
claiming the parser, job table, or fork path is the bottleneck.
