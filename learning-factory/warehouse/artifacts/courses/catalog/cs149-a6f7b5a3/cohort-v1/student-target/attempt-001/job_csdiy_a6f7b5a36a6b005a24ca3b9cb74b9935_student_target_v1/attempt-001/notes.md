# Kickoff learning notes

Scope: only the supplied parallel-computing kickoff unit. These notes do not
claim completion of CMU 15-418, Stanford CS149, or any broader course.

## Initial contract checklist

- Histogram domain: exactly 256 byte values.
- Oracle: a deliberately direct sequential counting loop.
- Parallel ownership: immutable input; one local histogram and one exception
  slot per worker; parent-only final merge after joins.
- Boundary policy: reject zero threads; use no workers for empty input; use
  `min(N, T)` workers otherwise.
- Evidence order: finish deterministic correctness tests first, then time the
  same generated inputs.

## Concrete hypotheses to test

| ID | Pre-measurement hypothesis | Evidence that could reject it |
|---|---|---|
| H1 | Balanced contiguous partitioning matches the oracle for remainder cases and `T > N`. | Any 256-bin mismatch or failed conservation check around a partition boundary. |
| H2 | Worker-private counters plus join-before-merge are race-free. | A race-sanitizer report or inspection showing concurrent writes to one object. |
| H3 | One-thread parallel execution is slower than sequential execution. | A stable median parallel time at or below the same-run sequential median. |
| H4 | Larger inputs benefit from a small number of workers and then flatten. | Medians that continue scaling across the tested local cap, or never improve at all. |

## Planned experiments

1. Hand-checkable, empty, singleton, skewed, deterministic random, partition
   boundary, excessive-thread, invalid-thread, and injected worker-failure tests.
2. A normal warning-enabled release build and ordinary test run.
3. One bounded sanitizer build if the local compiler supports it; record failure
   honestly if the runtime is unavailable.
4. After correctness passes, two moderate generated sizes, thread requests
   `1, 2, 4`, one warm-up, and at least seven retained repetitions.

## Running observations and lessons

### Hypothesis outcomes

| ID | Outcome in this unit | Limit |
|---|---|---|
| H1 | Supported by known-value, boundary, seeded, skewed, empty, singleton, and `T > N` tests; every measured row also matched and conserved counts. | Tested cases are finite. |
| H2 | The ownership audit found no shared worker-written location, and joins order parent reads after worker writes. | No dynamic race result: ThreadSanitizer could not link locally. |
| H3 | Supported in all 18 one-worker measurements. Median paired speedup was 0.530 at 4 MB and 0.426 at 32 MB. | Magnitudes are machine-specific and noisy. |
| H4 | Not established. Parallel median throughput rose through four workers, but paired speedups crossed 1.0 and varied widely. | Shared-worker scheduling, topology, and frequency were unknown. |

### Experiment record

- GNU C++ 8.5.0 Release build compiled with warnings and no warning output.
- Four CTest entries passed. The unit harness covers all 256-bin equality,
  conservation, partition boundaries, fixed seeds, excessive threads, invalid
  zero threads, and an injected worker exception.
- Explicit CLI cases confirmed `N=3,T=8` uses three workers and `N=0,T=8` uses
  zero; both matched the oracle and conserved counts.
- ThreadSanitizer and UndefinedBehaviorSanitizer configurations compiled object
  files but failed while linking because the respective runtime libraries were
  missing. This is recorded as unavailable evidence, not a passing result.
- Fifty-four timed rows were retained for two sizes and three thread counts.
  Every row carries `oracle_match=true`, `conservation=true`, and an explicit
  observed-run validation label in `benchmark_raw.csv`.

### Production-engineering lessons

1. Boundary behavior belongs in the interface, not just tests. In particular,
   empty input and invalid thread count are independent concerns.
2. A worker exception needs a transport and join policy. Catching it only to
   keep the process alive would still be wrong if a partial result escaped.
3. End-to-end API timing changes the question: fresh thread creation and result
   combination are real costs for this interface even though they are not the
   counting loop.
4. Median-only reporting would have hidden substantial temporal drift. Raw
   samples and ranges prevented a fragile “four threads are faster” claim.
5. Tool availability is part of evidence provenance. Sanitizer flags compiling
   is not the same as an instrumented test run.

No optional public reference or external course material was consulted.
