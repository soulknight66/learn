# Benchmarking stage

This is a measurement protocol, not evidence that Pebble has been benchmarked.
No timings or performance claims are included in the revealable tree.

## Measurement questions

Measure separate operations so that a result answers a clear question:

- tokenization of a fixed source string;
- parsing pre-tokenized or repeatedly tokenized input, with the choice stated;
- compilation of an already-built AST;
- tree execution of an already-built AST;
- VM execution of already-built bytecode; and
- complete `run` pipelines for both backends.

Use deterministic programs representing a long arithmetic expression, a
state-mutating counted loop, and branch-heavy control flow. Validate every
workload before timing it, and exclude setup or source generation unless the
benchmark is explicitly about that work.

## Procedure

1. Record operating system, architecture, runtime name and version, command,
   commit, and whether the machine was otherwise loaded.
2. Warm each operation before sampling. Do not report warm-up observations.
3. Collect multiple samples containing multiple iterations. Report the sample
   distribution and iteration count, not only the fastest observation.
4. Randomize or rotate operation order if comparing backends in one process.
5. Consume or verify results so an optimizing runtime cannot discard work.
6. Run the sealed oracle and fixed learner entry point separately, compare both
   with expected observations, and bind the report to content digests before timing.

Results from different workload sizes or machine/runtime configurations are not
directly comparable. A sealed harness and deterministic workloads are provided
for evaluators; any numbers it later produces must be recorded as observed
results, not copied into this protocol.
