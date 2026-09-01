# End-to-end microbenchmarks

`run.py` measures fresh-process `minish -c` workloads. It is a regression tool,
not a production-performance claim: startup, dynamic linking, process creation,
filesystem caches, scheduler load, and host power policy all affect results.
No benchmark numbers are checked into this repository.

The harness requires Python 3.6 or newer and the standard `ps` utility, which it
uses to clean every process group in a timed-out disposable session. Build and
run:

```sh
make -C starter
python3 benchmarks/run.py --iterations 20 starter/minish
```

Emit machine-readable results for a later comparison:

```sh
python3 benchmarks/run.py --iterations 30 --json starter/minish \
  > /tmp/minish-benchmark.json
```

Every timed sample starts a new shell process, captures no command output, and
must finish before a bounded timeout. The workloads cover:

- shell startup and a parent-run built-in;
- parser/list traversal dominated by built-ins;
- one external command;
- a finite two-stage bulk-data pipeline;
- a longer low-volume pipeline;
- a burst of short asynchronous jobs followed by `jobs`.

## Interpreting evidence

Compare the same executable configuration on the same otherwise idle host. Run
the complete suite several times, alternate revisions to reduce warm-cache
bias, and retain raw JSON plus compiler flags and commit identity. Median is a
useful center; p95 highlights occasional stalls but needs many samples before it
is stable.

A faster incorrect shell is still incorrect. Run functional and adversarial
tests first. In particular, a shell that fails to wait, drops output, skips
parsing, or leaks background work may appear artificially fast. Treat a change
as a suspected regression only when its magnitude is repeatable and larger than
run-to-run noise, then profile or trace before optimizing.

The harness reports observations from the local run only. It assigns no
`BENCHMARKED` validation label and contains no reference thresholds.
