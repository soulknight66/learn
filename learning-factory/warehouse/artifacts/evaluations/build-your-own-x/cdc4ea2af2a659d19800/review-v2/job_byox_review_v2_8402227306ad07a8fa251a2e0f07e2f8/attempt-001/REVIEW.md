# Independent review

Verdict: **FAIL**. The submission is not usable or reproducible as delivered, and an
independent test found a contract violation shared by all three reference architectures. No
validation target is promoted by this review.

## Prioritized findings

### P0 — The challenge cannot be built or attempted from the submitted artifact

Every allocator and test includes `allocator.h`, while the learner instructions explicitly
point to `include/allocator.h`; that file and the entire `include/` directory are absent. The
documented `scripts/build_all.py` and `scripts/` directory are also absent. Consequently:

- `python3 CANDIDATE/scripts/build_all.py` exits 2 because the file does not exist.
- A strict compile of the reference plus public contract exits 1 because `allocator.h` cannot
  be found.
- The starter has no API declarations to implement against, so this blocks learner use as well
  as independent validation.

The candidate needs the public API header and a deterministic build/validation entry point,
with an inventory check that fails packaging if a documented required file is omitted.

### P1 — All three implementations accept caller-declared overlapping spans

`REQUIREMENTS.md:11-15` defines a state region and arena span as disjoint and says
initialization rejects overlapping spans. The implementations validate the minimum
`state_bytes`, but calculate the state interval using only `sizeof(state)`:

- `sealed/reference/allocator.c:121-132`
- `sealed/alternatives/best_fit/allocator.c:123-134`
- `sealed/alternatives/segregated_bins/allocator.c:151-162`

An independent harness supplied a state extent larger than `lf_state_size()` and placed the
arena after the implementation-used prefix but inside that declared extent. Every architecture
returned `LF_OK` instead of `LF_ERR_ARGUMENT`. This contradicts the published API contract and
means callers cannot rely on the supplied extents being validated. The overlap calculation
must use the declared state span with overflow-safe endpoint checks, or the public contract and
parameter meaning must be narrowed explicitly.

### P1 — Benchmark and validation evidence cannot be reproduced from the candidate

`benchmarks/run.py` depends on three `validation-output/bin/*-benchmark` executables and
`validation-output/toolchain.json`; none are present, and the missing build script cannot create
them. With Python 3.11 the runner fails on the first missing executable. The default Python here
is 3.6.8 and fails even earlier on `from __future__ import annotations`, while the requirements
only say “Python 3.”

The existing `benchmarks/results/smoke.json` has consistent arithmetic, and a diagnostic rebuild
reproduced its deterministic fragmentation fields. That is useful corroboration, but it is not
independent benchmark validation: the file contains an absolute include path into
`job_project_allocator_vertical_v1/attempt-002`, and the submitted pack has no corresponding
binaries, toolchain record, controller exit codes, or logs. It also lacks an explicit validation
label/provenance link. Documentation says the result is absent at generation time while the
manifest still labels this artifact `GENERATED_CANDIDATE`, leaving the artifact phase ambiguous.

Ship a relative, self-contained build path; state the minimum Python version; retain
controller-owned command/exit/log evidence; and label generated results explicitly. Do not use
the submitted smoke file alone to award `BENCHMARKED`.

### P1 — Progressive disclosure is organized but not enforced

Reference implementations, expected answers, patches, and sealed tests are placed under twelve
sealed-named files. This is a sensible directory boundary, but the only protection is prose:
“Do not expose `sealed/` to a learner workspace.” No submitted allowlist, view builder, or
deterministic packaging check shows that nested sealed directories are excluded. In particular,
answers also occur under `debugging/.../sealed/` and `review_exercises/.../sealed/`, so filtering
only the top-level `sealed/` would still leak solutions.

Add a controller-enforced learner-view allowlist and an isolation test that asserts no sealed
reference, expected answer, or hidden contract is present in the resulting view.

### P2 — The generated pack has no explicit reuse license

`PROVENANCE.json` records the catalog commit and CC0 status, marks the linked tutorial
`NOASSERTION`, says its content was not mirrored, and identifies generated versus inferred
material. Those are good boundaries. However, “newly agent-generated” is not a license grant,
and the candidate has no `LICENSE`, `NOTICE`, or SPDX identifiers for its own C and educational
content. Add an explicit license for the generated pack while preserving the existing catalog
and outbound-link boundary.

### P2 — The model's non-overlap claim is stronger than its check

The deterministic model is honestly described as one fixed-seed model rather than a general
fuzzer, and it checks tags, bounds, alignment, resize preservation, and invariants. It does not
perform a pairwise live-range overlap comparison: overlap is detected indirectly when tags
differ, so equal-tag overlaps can be missed. Add explicit interval comparisons and independent
boundary cases, including the declared-span overlap case above.

### P2 — The runner does not meet the stated subprocess isolation invariant

The runner correctly uses an argv array, captured output, and a 20-second timeout. It does not
start the benchmark in a new process group or terminate a group on timeout. That is harmless for
the current single-process benchmark in normal operation, but it does not satisfy the repository
rule for bounded subprocess cleanup.

## Validation-claim disposition

The manifest names targets, not achieved statuses. Builder-authored prose, tests, scripts, and
result JSON were therefore treated only as material to inspect.

| Label | Disposition | Basis |
|---|---|---|
| `BUILDS` | Rejected | Native build is blocked by the missing header and build script. |
| `TESTED` | Rejected | Diagnostic tests required a reconstructed header; an independent contract test fails. |
| `FUZZED` | Not established | The pack correctly calls its one-seed workload model checking, not fuzzing. |
| `BENCHMARKED` | Rejected | Historical raw JSON is not independently replayable from the submission. |
| `REVIEWED` | Not awarded to the manifest | The included expected review is builder material; this report is external evidence only. |
| `TRANSFER_VERIFIED` | Not established | No learner-view transfer artifact or isolation proof is supplied. |
| `PRODUCTIONIZED` | Correctly disclaimed | Manifest and prose consistently say `NOT_PRODUCTION_READY` and `PARTIAL`. |

## Material that held up under review

- All three metadata documents parse, and benchmark arithmetic is internally consistent.
- With a temporary inferred header, strict GCC builds succeeded and the submitted public,
  sealed-contract, model, debugging, review, and bin-integrity fixtures behaved as described.
- Direct benchmark runs reproduced all stored deterministic allocation/fragmentation counts;
  only timing varied, as the documentation appropriately warns.
- Static inspection found no prohibited `malloc`, `calloc`, `realloc`, `free`, `sbrk`, or `mmap`
  call in any of the three allocator implementations.
- The production limitations and tutorial-license uncertainty are stated candidly.

These positives do not overcome the missing public/build artifacts or the independently
reproduced overlap-contract failure.
