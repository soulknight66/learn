# Study Task: A Trustworthy Parallel Histogram

## Mission

Create a small production-minded C++17 project that counts occurrences of every possible byte value (`0` through `255`) in an input. Provide a sequential reference implementation and a parallel implementation using standard C++ threads. The parallel result must exactly match the reference; only then should you measure performance.

Keep the project offline and dependency-light. CUDA, MPI, OpenMP, Spark, distributed execution, and external course assignments are outside this unit.

## Required behavior

Define and document a stable interface for both implementations. At minimum, a caller must be able to supply a byte sequence and, for the parallel version, a requested positive thread count. Each implementation returns 256 nonnegative integer counts.

Your documented contract must cover:

- empty, one-byte, and small inputs;
- inputs whose size is not divisible by the requested thread count;
- a requested thread count larger than the input;
- invalid thread-count input, including zero;
- the count type and the supported maximum input size;
- how worker failures are surfaced rather than silently ignored.

The program must also offer a documented command-line route for running correctness checks and benchmarks. It may read a binary file, deterministically generate bytes from an explicit size and seed, or support both. A fresh evaluator must be able to discover the commands from your README without reading source code.

## Engineering constraints

- Use C++17 or later and only locally available build/runtime dependencies.
- Use `std::thread` for the parallel implementation. Do not merely invoke a parallel library algorithm.
- Keep input generation and file I/O outside the timed histogram region.
- Avoid undefined behavior and data races. Do not suppress or discard worker exceptions.
- Make correctness runs deterministic for a given input, size, seed, and thread count.
- Keep each single test or benchmark invocation bounded; do not rely on huge inputs to demonstrate care.
- Do not check in compiled binaries, caches, or machine-specific build products.

You choose the decomposition and synchronization strategy. Record alternatives you rejected and why; do not assume that using more threads must be faster.

## Work stages

### 1. Write the design note

Before measuring performance, create `DESIGN.md` containing:

- the public contract and key invariants;
- a simple work/span model using input size `N` and requested threads `T`;
- the ownership of every piece of mutable state during parallel execution;
- expected overheads and at least two plausible failure modes;
- one alternative design and the reason you did not choose it.

Revise the note if implementation evidence disproves an assumption. Mark revisions rather than presenting hindsight as an original prediction.

### 2. Build the program

Organize the sequential and parallel logic behind testable interfaces, not only inside `main`. Provide a reproducible build configuration such as CMake or Make and use compiler warnings appropriate to your toolchain.

The command-line program must report enough context to reproduce a run: input source or generator parameters, input size, requested and actually used thread counts, and whether the parallel result matched the sequential result. Use a stable, machine-readable form for benchmark rows.

### 3. Establish correctness evidence

Add automated tests that include:

- hand-checkable inputs with known counts;
- empty and singleton inputs;
- skewed data, such as all bytes equal;
- sizes around partition boundaries;
- multiple fixed seeds and multiple thread counts;
- requested threads greater than the number of input bytes;
- invalid arguments and the failure behavior promised by your contract.

For generated cases, compare all 256 parallel counters with the sequential oracle. Also check the conservation invariant that the sum of counters equals the input length. Make a test failure return a nonzero status.

If your environment provides a thread or undefined-behavior sanitizer, record a bounded sanitizer run as supplemental evidence. The ordinary test suite must still work without an optional sanitizer.

### 4. Measure without overclaiming

After tests pass, benchmark at least two nontrivial input sizes and the usable subset of thread counts `1, 2, 4, ...` up to a documented local cap. Use one untimed warm-up and at least seven measured repetitions for each configuration. Keep raw per-repetition durations; do not retain only the best result.

Record the compiler and flags, build type, operating system, processor information available through ordinary tools, input seed, input sizes, thread counts, timed-region definition, and whether the machine was shared. Report a robust summary such as the median, along with spread or individual observations. Include sequential time, parallel time, speedup relative to the same sequential baseline, and throughput.

If a run is slower, noisy, or limited to one hardware thread, preserve and discuss that result. It is evidence, not a reason to invent a speedup.

### 5. Submit a concise analysis

Create `REPORT.md` that:

- separates predicted behavior, observed measurements, and possible explanations;
- includes or links to the raw benchmark table;
- identifies the tested machine and the limits of generalizing from it;
- explains at least one case where overhead or memory behavior constrains speedup;
- proposes one next experiment without claiming to have performed it.

Answer every prompt in `COMPREHENSION.md` in a separate `COMPREHENSION_ANSWERS.md` file in your submission.

## Submission contents

Submit source, build configuration, tests, `README.md`, `DESIGN.md`, `REPORT.md`, raw benchmark data in CSV or JSON form, and `COMPREHENSION_ANSWERS.md`. The README must give exact clean-build, test, correctness-run, and benchmark commands.

Stop after this bounded unit. Do not import an external CS149/15-418 assignment or describe this work as completion of the broader course.
