# Independent review

## Verdict

**FAIL.** The submission is not a self-contained learner artifact and cannot execute its own documented validation path. The source bodies show useful educational work in reviewer-assisted diagnostics, but those diagnostics cannot replace omitted submitted interfaces, harnesses, or controller-owned evidence.

## Prioritized findings

### P0 — Required public interface and build harness are missing

`CANDIDATE/README.md:14` and `CANDIDATE/REQUIREMENTS.md:3` direct the learner to `include/allocator.h`; every allocator and contract includes that header, but it is absent. `CANDIDATE/README.md:20` says validation runs `python3 scripts/build_all.py`, but `scripts/build_all.py` and the entire `scripts/` directory are absent.

Observed consequences:

- The documented command exits 2 with `can't open file 'scripts/build_all.py'`.
- Ten of thirteen C translation units fail at `allocator.h: No such file or directory`; only the standalone sanitizer and review-exercise sources pass syntax-only compilation.
- The learner cannot know the API declarations, status constants, or statistics structure, so the starter is not implementable as shipped.

This is a release-assembly blocker, not a documentation polish issue. Regenerate the candidate with its public API and deterministic build/validation harness, then validate that exact assembled artifact.

### P0 — Progressive disclosure has no enforceable boundary

`CANDIDATE/README.md:15` says not to expose sealed material to a learner, yet complete answers are directly readable at `CANDIDATE/sealed/DESIGN.md:3`, `CANDIDATE/debugging/coalesce-span/sealed/root-cause.md:3`, and `CANDIDATE/review_exercises/rounding-overflow/sealed/EXPECTED_REVIEW.md:3`. Neither the manifest nor a submitted projection script defines a learner-visible allowlist or proves a filtered view.

Keeping sealed material in a controller package can be valid, but prose is not an isolation control. A deterministic controller-owned projection and a test that asserts the learner view contains none of these paths are required before distribution.

### P1 — The benchmark artifact is plausible but detached from reproducible evidence

`CANDIDATE/benchmarks/run.py:23` requires three absent `validation-output/bin/*` programs and line 45 requires absent `validation-output/toolchain.json`. The stored report embeds an absolute header path from a different workspace at `CANDIDATE/benchmarks/results/smoke.json:18-28`. It contains no source or binary hashes, build return codes, captured logs, validator identity, or explicit evidence-to-label mapping. `CANDIDATE/PROVENANCE.json:25-28` mentions toolchain and controller evidence, but those artifacts are not submitted.

The JSON parses, its throughput and fragmentation formulas recompute, and reviewer-assisted runs reproduced its deterministic non-timing fields. Those facts make the report plausible; they do not attribute it to this incomplete candidate or prove `BENCHMARKED`. Its presence also sits uneasily with `GENERATED_CANDIDATE` (`MANIFEST.yaml:31`) and prose saying generation does not create the result (`README.md:23-24`; `benchmarks/README.md:6`). Record a clear artifact stage and durable provenance when evidence is attached.

### P1 — All implementations accept overlapping declared spans prohibited by the contract

`CANDIDATE/REQUIREMENTS.md:11-15` says the caller supplies state and arena spans and initialization rejects overlap. The implementations calculate `state_end` with `sizeof(state)` rather than the supplied `state_bytes`:

- reference: `sealed/reference/allocator.c:127-135`
- best-fit: `sealed/alternatives/best_fit/allocator.c:129-137`
- segregated bins: `sealed/alternatives/segregated_bins/allocator.c:157-165`

A reviewer-authored test passed a 512-byte declared state span and an arena beginning 256 bytes into it. All three returned `LF_OK`. The included withheld test checks only identical base addresses (`sealed/reference_tests/contract.c:33-37`), so it misses this case. Either enforce non-overlap using the declared span or narrow the written contract explicitly.

### P1 — Validation coverage and harness containment are insufficient

The supplied tests do not assert that each expected binary reports the matching architecture or exercises the promised placement policy. The runner keys results by filename (`benchmarks/run.py:22-43`) but does not validate the parsed `architecture`, so one implementation linked under all three names could pass that layer. Exact aligned capacity/statistics and logical-span canaries are also not asserted before benchmark code trusts the statistics. Nothing in the submitted validators enforces the ban on allocator-internal heap calls (`REQUIREMENTS.md:18`); the current implementations contain no such calls, but a learner implementation could evade this contract without link/symbol or interposition checks.

Additionally, `subprocess.run` at `benchmarks/run.py:25-38` uses an argv array, timeout, and captured streams, but no process group/session. That violates the repository requirement that bounded subprocesses use process groups so descendants can also be terminated.

Add controller-owned negative/edge tests, architecture-to-binary checks, exact statistics assertions, outside-span canaries, and process-group termination. Builder-authored scripts and tests still must not self-award validation labels.

### P2 — Environment and portability requirements are underspecified

`CANDIDATE/environment/README.md:3` requires only “Python 3,” but the default Python 3.6.8 rejects `benchmarks/run.py:1`; Python 3.11.5 parses it and then reaches the missing-binary failure. State the actual minimum Python version.

The README calls the contract portable C11 (`README.md:7`), while all implementations require optional `uintptr_t` and perform adjusted pointer-to-integer-to-pointer conversions (for example, `sealed/reference/allocator.c:112-150`). Those operations are supported by the tested GCC/x86-64 environment but are not guaranteed by every conforming C11 implementation. Narrow the portability claim or redesign/document the platform assumptions.

### P2 — Provenance boundary is clear, but reuse rights for the pack are not

`CANDIDATE/PROVENANCE.json:34-37` usefully distinguishes CC0 catalog metadata from the `NOASSERTION` outbound tutorial and says tutorial content was not mirrored. However, “newly agent-generated” is provenance, not a license grant. No `LICENSE`, `COPYING`, `NOTICE`, or SPDX identifier applies to the generated code and teaching material. Add an explicit license without implying rights over the linked tutorial. Network and upstream-source access were unavailable, so the non-copy assertion and external license metadata remain unverified.

## Claim disposition

| Label | Disposition | Basis |
|---|---|---|
| `BUILDS` | Not established | Native documented build and strict compilation fail on omitted files. |
| `TESTED` | Not established | No candidate-native/controller-owned successful test run exists. Reviewer scaffolding is diagnostic only. |
| `FUZZED` | Not claimed or established | The pack correctly calls its fixed-seed model non-exhaustive and not a fuzzer (`adversarial/README.md:7-8`). |
| `BENCHMARKED` | Not established | Stored JSON is internally consistent but detached and not reproducible from the submission. |
| `REVIEWED` | Not established | The sealed expected review is author-provided teaching content, not independent validation evidence. |
| `TRANSFER_VERIFIED` | Not established | No transfer artifact or receiving-environment check was submitted. |
| `PRODUCTIONIZED` | Correctly false | `MANIFEST.yaml:18,26` and `README.md:26-28` clearly deny production readiness. |

## Useful material retained in the assessment

The requirements, concepts, design questions, intentional debugging mutation, and overflow review exercise form a thoughtful learning sequence. The manifest is appropriately conservative: it says `GENERATED_CANDIDATE`, lists validation targets rather than achieved statuses, and says `NOT_PRODUCTION_READY`; `PARTIAL` likewise appears only as a target. With a reviewer-owned inferred header outside `CANDIDATE`, all three source implementations compiled strictly and passed both included checks and an independent deterministic stress test; the deliberate bug and overflow demonstrations also behaved as described. These positives justify preserving the educational design while rebuilding the deliverable and its evidence chain.

See `VALIDATION.md` for exact commands, results, and limitations.
