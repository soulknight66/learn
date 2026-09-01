# Repeatable microbenchmarks

`run.sh` measures the wall-clock cost of successful `create`, `ps`, and
`delete` CLI invocations in an isolated temporary state directory. It prints
raw tab-separated samples; `summarize.awk` derives basic aggregates without
discarding the raw evidence.

From the repository root:

```bash
bash benchmarks/run.sh ./starter/minictr 50 >results.tsv 2>results.log
awk -f benchmarks/summarize.awk results.tsv
```

The iteration count must be between 1 and 10,000. The runner uses an empty
directory as rootfs, suppresses ordinary command output, stops on the first
failed operation, bounds each invocation with `timeout`, and removes its
private `MINICTR_HOME` afterward. The log
records the target, Bash version, kernel, iteration count, and clock source.
The runner uses Bash's microsecond clock when available and otherwise requires
a `date` implementation with `%N` nanosecond support.

These are process-launch microbenchmarks, not container workload benchmarks.
They do not measure namespace setup, filesystem I/O inside a container,
parallel scalability, resident memory, security, or production capacity.
Results depend heavily on the host, filesystem, shell, cache state, and load;
do not compare numbers without retaining the raw TSV and log from both runs.
No benchmark result is checked into this challenge pack.
