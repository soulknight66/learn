# Diagnostic benchmark harness

`bench_host.c` times 100,000 scheduler rotations and prints a checksum so the
loop remains observable. It is a host microbenchmark only: it excludes assembly
switch cost, cache/TLB behavior, UART, QEMU, and all filesystem/VM operations.

Shared factory timing is not a stable performance baseline. The generated pack
does not claim a threshold and `MANIFEST.yaml` has no `BENCHMARKED` label. If an
independent evaluator runs this harness, it should record compiler, flags, host,
sample count, dispersion, and raw output rather than promoting one elapsed value
as a kernel result.

Build or run explicitly with a compatible host compiler:

```sh
make -C benchmarks clean all CC=/absolute/path/to/cc
make -C benchmarks run CC=/absolute/path/to/cc
```
