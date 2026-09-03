# Sealed benchmark workloads

`workload.ec` is a deterministic execution workload.  It prints a checksum so
a harness can reject miscompiled runs.  It is intentionally not timed by the
factory build step, and no benchmark number is recorded.

A valid benchmark protocol should compile once, redirect or bound output, run
in fresh processes, retain raw samples, and treat the native/guest tower as a
separate workload because dispatch amplification is substantial.
