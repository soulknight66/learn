# Benchmark protocol (not executed)

No benchmark numbers or profiler output were produced. The artifact is not labeled BENCHMARKED.

A future independent run can measure three separate workloads after recording compiler version,
flags, machine/OS, executable digest, and repetitions:

1. lexer/compiler throughput on generated valid functions with no runtime work;
2. VM dispatch throughput on a fixed-count arithmetic loop;
3. call-frame cost using bounded recursive and iterative equivalents.

Use an external wall-clock tool with warmups, at least 20 measured subprocess runs, and median plus
dispersion. Keep source and step budgets constant. Capture stdout separately so terminal speed does
not dominate. Do not compare this fixed-capacity teaching implementation to an ISO C compiler as if
they implemented the same semantics.
