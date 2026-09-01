# Benchmark guidance

No benchmark label or performance number is claimed for this generated artifact.
Timing inside a shared build worker would not be portable evidence.

For a controlled follow-up, generate fixed Mica workloads in three groups:

1. long straight-line arithmetic to isolate expression walking and emission;
2. loop-heavy execution to compare interpreter dispatch with native branches;
3. maximum-size symbol tables to expose linear lookup during validation.

Record source hash, tool binary hash, compiler and flags, CPU/OS, warmup policy,
sample count, wall and CPU time, peak resident memory, exit status, and output
hash. Run build/parse, interpreter execution, assembly emission, linking, and
native execution as separate measurements. Correctness checks must precede
timing, and generated output must not be discarded in a way that lets the host
optimizer remove the workload.
