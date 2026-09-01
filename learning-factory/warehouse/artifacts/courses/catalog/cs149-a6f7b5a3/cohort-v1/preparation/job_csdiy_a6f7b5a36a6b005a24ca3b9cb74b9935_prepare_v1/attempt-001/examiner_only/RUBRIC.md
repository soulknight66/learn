# Independent Examiner Rubric: Trustworthy Parallel Histogram

This rubric evaluates only the bounded kickoff unit. It must not be interpreted as evidence that the learner completed CMU 15-418, Stanford CS149, or a full parallel-computing course.

## Evaluation protocol

Score produced evidence, not assertions in the learner's report. Begin from a clean copy with no network access. Record the compiler version, exact build/test commands, exit statuses, and relevant logs. Keep each evaluator invocation bounded with a timeout and avoid shell-string execution in an automated harness.

The examiner may add private input cases through the project's public interface, but must not copy private cases or this rubric into a learner-facing directory. If the interface prevents independent cases, score the corresponding correctness and testability criteria accordingly.

Recommended checks include empty input; all 256 byte values; all-equal data; lengths `1, 2, 3, 255, 256, 257, 4095, 4096, 4097`; fixed pseudorandom inputs; thread requests `1, 2, 3, 4, 7` and values greater than `N`; invalid thread count zero; and repeated execution of the same case. On every accepted input, all 256 counters must equal the sequential oracle and their sum must equal `N`.

## Gating rules

- **Not assessable:** no source, source cannot be built after reasonable use of documented commands, or the submission requires unavailable network content. Record the failure; do not infer correctness from prose.
- **Maximum 49/100:** the parallel path is absent, is only a renamed sequential path, does not use `std::thread`, or routinely produces an incorrect result.
- **Maximum 59/100:** buildable parallel code exists, but there is credible evidence of a data race, unsafe lifetime, swallowed worker failure, or nondeterministic correctness failure.
- **Maximum 69/100:** correctness is credible but raw per-repetition benchmark evidence is absent or timing includes undocumented setup work, making the central performance claims unauditable.
- A sanitizer finding is evidence to investigate, not an automatic verdict if it originates outside learner code. Preserve the diagnostic and justify the classification.

## Scored criteria (100 points)

### 1. Reproducible build and operable interface — 12 points

- **10–12:** Clean offline build and test commands work as documented; warnings are enabled; the CLI or equivalent public interface exposes reproducible input and thread parameters, gives meaningful failures, and reports actual run context.
- **6–9:** The project builds and is usable with minor undocumented steps or weak diagnostics; core parameters remain testable.
- **1–5:** Significant manual repair, machine-specific assumptions, or a source-code-only interface obstructs independent evaluation.
- **0:** Not buildable or not operable.

### 2. Sequential oracle and contract correctness — 16 points

- **14–16:** The reference implementation is simple and exact; it uses an adequate count type; the documented contract consistently handles empty, skewed, binary, and invalid inputs; conservation holds.
- **9–13:** Core results are correct, with a minor contract, type, or error-handling weakness.
- **1–8:** The reference works only for common cases or has material ambiguity that weakens its role as an oracle.
- **0:** No trustworthy reference result.

### 3. Parallel correctness and concurrency safety — 24 points

- **21–24:** All independent cases exactly match the oracle across thread counts; work coverage has neither gaps nor overlap errors; shared-state ownership and object lifetimes are sound; thread creation and worker failures cannot silently yield a successful partial result.
- **15–20:** Correct across broad cases with credible race freedom, but one boundary, lifetime, or failure path is weakly handled.
- **7–14:** Common cases pass, but edge behavior or synchronization reasoning is unreliable.
- **1–6:** A nominal parallel path exists but regularly fails or has unsafe concurrency.
- **0:** No genuine parallel implementation.

Expected technical evidence may use per-worker private histograms followed by a post-join reduction, correctly synchronized shared counters, or another demonstrably safe strategy. Do not require one particular strategy. A mutex or atomic design may be correct even if slower. Exact outputs alone do not rule out a latent race; inspect ownership/synchronization and consider a bounded sanitizer run where available.

### 4. Automated test quality — 14 points

- **12–14:** Deterministic tests cover known answers, all counters, conservation, empty/singleton/skewed cases, partition boundaries, `T > N`, invalid inputs, several seeds and thread counts, and return a failing process status on defects.
- **8–11:** Good oracle comparisons and normal coverage with one notable boundary or error-path omission.
- **3–7:** A few happy-path tests exist but would miss common partition or contract defects.
- **1–2:** Tests are manual or only check that the process runs.
- **0:** No executable correctness tests.

Examiner-injected tests count as product correctness evidence, not as credit for the learner's own test suite.

### 5. Measurement integrity and retained evidence — 16 points

- **14–16:** Raw observations include at least seven repetitions after warm-up for two meaningful sizes and multiple usable thread counts; input/setup is outside the stated region; build/machine/seed context is retained; summaries, throughput, and speedup are arithmetically consistent; noise and slower cases are preserved.
- **9–13:** Useful, mostly reproducible measurements with a small omission in metadata, repetition design, or summary treatment.
- **3–8:** Some timings exist, but best-of selection, setup contamination, missing raw rows, or inconsistent baselines materially limit conclusions.
- **1–2:** Anecdotal timing only.
- **0:** No timing evidence.

Do not award speedup points merely because a number exceeds 1.0. Check that numerator and denominator use the same workload and compatible timed regions.

### 6. Engineering design and maintainability — 10 points

- **9–10:** Interfaces separate algorithm, CLI, and measurement concerns; names/types communicate ownership; error paths are explicit; mutable state and invariants are documented; the design note records a real alternative and honest revisions.
- **6–8:** Generally clear structure with modest coupling, duplication, or documentation gaps.
- **2–5:** Working code is difficult to test or reason about because concerns are tangled or contracts live only in implementation detail.
- **0–1:** Structure prevents meaningful review or safe modification.

### 7. Analysis and comprehension — 8 points

- **7–8:** Responses accurately connect the learner's implementation and data to work/span, memory-model safety, edge cases, oracle limitations, timed-region choices, overhead hypotheses, reproducibility, and bounded future work. Claims are explicitly scoped to evidence.
- **4–6:** Most concepts are sound, but answers are generic or one major claim lacks evidence.
- **1–3:** Several misconceptions appear, or responses repeat definitions without applying them.
- **0:** Missing or fundamentally nonresponsive.

Key distinctions expected across the responses: work is not the same as elapsed time; exact output does not prove absence of races; `T > N` and `N = 0` require explicit safe behavior; thread creation, memory traffic, combination, scheduling, and noise are separate speedup hypotheses; and a single-machine benchmark supports only a qualified local claim.

## Result record

Record the numeric score, applied cap (if any), validator commands and exit statuses, validation label, artifact locations, and a short evidence-based rationale. A passing threshold, if the surrounding job defines one, promotes only this unit and only through the harness-controlled validator. Otherwise report the score without inventing a pass state.
