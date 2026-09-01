# Benchmark protocol

The smoke workload opens an empty store, inserts fixed-size unique values with per-append fsync
disabled, then reads every value. The stated hypothesis is captured in the JSON before results.
Raw nanosecond totals, per-operation values, file sizes, interpreter/platform, and parameters are
written by the harness. Numbers are machine-specific and should not be treated as universal.
