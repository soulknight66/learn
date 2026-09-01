# Revision learning notes

Scope: this is the same target learner revising only the supplied parallel
histogram kickoff. It does not claim completion of CMU 15-418, Stanford CS149,
or any broader course, and it does not claim that an independent transfer or
evaluation has occurred.

## What changed after the examiner feedback

The prior handoff named implementation and evidence files that were absent from
the examiner-visible workspace. This revision addresses that concrete defect by
placing the actual source, build configuration, tests, design, answers, report,
raw measurements, metadata, and validation logs in this workspace beside the
harness-facing narrative files. `ARTIFACT_MANIFEST.sha256` records the staged
file set so an omitted or changed path can be detected before building.

No algorithm rewrite was inferred from the zero score. The feedback found the
attempt unassessable rather than identifying a histogram misconception. The
implemented design therefore tests the previously described ideas directly:
immutable input, contiguous balanced ranges, one private 256-bin array and one
exception slot per worker, join-before-merge, and no partial return on failure.

## Contract lessons retained

- Thread count zero is invalid even when the input is empty.
- Empty input uses zero workers; otherwise the actual count is `min(N, T)`.
- `std::uint64_t` bins support input length through
  `min(Bytes::max_size(), UINT64_MAX)`, subject to allocation.
- Remainder bytes belong to the first `N mod W` contiguous ranges.
- A caught worker exception is transported to the parent, which joins every
  worker before rethrowing. Partial thread-launch failure also joins workers
  already created.
- Exact oracle equality is paired with conservation and hand-computed cases;
  it is not treated as proof of race freedom.

## Concrete experiment outcomes

| Experiment | Observation | Evidence boundary |
|---|---|---|
| GCC 8.5.0 Release build with five warning classes | All three targets compiled; no diagnostic was emitted. | Build success does not establish runtime correctness. |
| Fresh CTest run | 4/4 entries passed in 0.08 seconds. | The cases are deterministic but finite. |
| `N=3,T=8`; `N=0,T=8`; `N=4099,T=7` | Used 3, 0, and 7 workers; every case matched all bins and conserved input length. | These executions do not cover all sizes/schedules. |
| Zero-thread CLI call | Rejected with exit status 2. | Covers the documented invalid-thread boundary. |
| Injected worker 2 exception | Unit test observed the original runtime error at the caller. | A deterministic seam tests transport, not every possible system failure. |
| Thread/undefined-behavior sanitizers | Both compiled objects but failed to link because their runtime libraries were absent. | No sanitizer pass is claimed. |
| Six benchmark configurations, nine repetitions each | All 54 rows passed oracle and conservation checks. One worker lost in every pair; two helped in both medians; four did not improve median throughput over two. | Shared/uncontrolled machine, unknown processor model/topology, and broad sample variation. |
| Independent CSV consistency calculation | Found 54 rows, nine per expected configuration, and recomputed every speedup/throughput field within printed precision. | Checks retained data consistency, not timer accuracy. |

## Measurement lesson

Median-only claims would conceal material variation. At 32 MB/two workers,
paired speedup ranged from 0.749 to 1.981; at 4 MB/four workers it ranged from
0.899 to 1.512. The appropriate conclusion is limited to the retained machine,
build, workload, and repetitions. A controlled randomized-block rerun is a next
experiment in `REPORT.md`, not work claimed here.

## Handoff lesson

An artifact map is navigation, not evidence. The receiving workspace needs the
files themselves, a build executed from that staged copy, durable outputs, and
a deterministic inventory. Even after doing those things here, only the
orchestrator or another evaluator can establish that a subsequent transfer is
complete.

No optional public reference, external course content, solution repository,
sealed material, factory state, or another learner's work was consulted.
