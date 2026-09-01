# Benchmark protocol

The smoke workload compares the reference with the instrumented teaching variant stored under
the legacy `production/` path. It opens an empty store, inserts fixed-size unique values with
per-append fsync disabled, then reads every value. The stated hypothesis is captured in the JSON
before results. Raw nanosecond totals, aggregate per-operation values, file sizes,
interpreter/platform, and parameters are written by the harness. Numbers are machine-specific,
do not establish production readiness, and should not be treated as universal.
