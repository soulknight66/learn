# Benchmark status

No benchmark was run and no `BENCHMARKED` claim is made. Capacities are tiny,
fixed constants, so timing these functions on a shared build host would mostly
measure harness and clock noise.

A meaningful extension would separate lookup-heavy, scheduler-heavy, and
full-file-copy workloads; record exact compiler flags and target; warm up the
emulator; report distributions rather than a single duration; and verify
results after every timed batch. Increasing capacities should be a parameter
in a separate experimental build, not an ABI change to the challenge.
