# Independent examiner rubric — managed kickoff unit 1

Validation label: **EXAMINER-ONLY REFERENCE; PREPARED, NOT A VALIDATION RESULT**  
Applies to: `managed_unit_01_finite_signals_lti_engineering`  
Maximum: 100 points; recommended validation threshold: 80, subject to the critical caps below.

This rubric is independent of the learner's self-report. Examine only the submitted artifacts and validator-controlled executions. Do not require network access or unavailable EE120 materials. A prose claim, a learner-generated passing log, or benchmark JSON is not proof until the harness reproduces or checks it.

## Preflight and critical caps

Run, in a bounded process from the attempt root:

```bash
python3 -m unittest discover -s submission -p 'test_*.py' -v
PYTHONPATH=submission python3 submission/benchmark.py
```

Retain stdout, stderr, exit status, and generated evidence through the harness. Apply these caps after ordinary scoring:

- Missing or unimportable `signals.py`, or no functioning convolution implementation: **maximum 49**.
- Submitted tests fail under the validator environment: **maximum 69**.
- Either convolution function calls/aliases the other, or a third-party convolution routine supplies the result: no credit for the affected implementation and **maximum 69**.
- Benchmark evidence is fabricated, cannot be regenerated, times input creation/JSON output, or reports disagreement as agreement: **maximum 69**.
- Missing comprehension responses or report: **maximum 79**.
- Any claim that this work completes EE120/the whole course, or that it is an official EE120 lab: **maximum 79** and flag the provenance defect.

A cap is not an automatic score. Preserve failed evidence. Only the harness-controlled validator may promote the unit, and validation can promote it only to `UNIT_1_COMPLETED_COURSE_STILL_IN_PROGRESS`.

## 1. API contract and functional correctness — 35 points

### FiniteSignal model — 9 points

- 3: Correct consecutive-index representation, `value_at`, zero outside support, and immutable tuple exposure.
- 2: Nonempty leading/trailing zeros are preserved; empty inputs canonicalize to `(start=0, samples=())`.
- 2: Start/index/offset types and sample types are checked as specified; booleans are rejected.
- 2: Non-finite floats raise `ValueError`; public behavior is typed and documented.

### Shift — 5 points

- 3: For nonempty input, `shift(k)` keeps the tuple unchanged and changes start to `start + k`.
- 1: Empty input remains canonical.
- 1: Positive, negative, and invalid offsets behave correctly without mutating the input.

### Direct convolution — 10 points

- 7: Correct values across validator cases, including negative starts, unequal lengths, zeros, and floating values.
- 2: Correct start and exact required stored length; either empty operand gives canonical empty.
- 1: Clearly ordinary nested traversal and no operand mutation.

The reference definition for nonempty signals is:

`y.start = x.start + h.start`, `len(y) = N + M - 1`, and tuple-position result `y[r] = sum(x[p] * h[r-p])` over valid positions. This is linear, not circular, convolution.

### Sparse convolution — 8 points

- 5: Same observable result as the reference across validator cases, within justified floating tolerance.
- 2: Independent structure skips products involving exact-zero stored values.
- 1: Still preserves the full output representation, empty rule, and input immutability.

### Operand errors — 3 points

- 3: Both functions consistently reject non-`FiniteSignal` operands with `TypeError`.

Suggested examiner cases include empty/nonempty pairs; starts well away from zero; singleton impulse-like inputs; all-zero but represented inputs; boundary zeros; booleans, strings, iterators, NaN and infinities; and randomly generated small signals checked against an examiner-owned oracle.

## 2. Test quality — 20 points

- 5: Meaningful hand-derived examples with expected values independent of submitted convolution code.
- 4: Required boundary and invalid-input cases, including bool and non-finite values.
- 5: At least 100 deterministic generated pairs cover empty, dense, and zero-heavy inputs and compare implementations appropriately.
- 4: At least three non-vacuous mathematical properties; generated data and assertions could expose realistic index/value defects.
- 2: Float comparison policy is consistent and explained; tests are deterministic, bounded, and readable.

Do mutation-test spot checks where practical: alter a local copy or monkeypatch a sign, output length, or offset expression and confirm relevant submitted tests fail. Implementation agreement alone earns no independent-oracle credit.

## 3. Engineering quality and report — 15 points

- 4: Cohesive names, small responsibilities, useful type hints/docstrings, no unnecessary dependency or global state.
- 3: Contract choices and mathematical-to-API mapping are clearly explained.
- 3: Complexity uses `N`, `M`, `Kx`, and `Kh` and includes allocation/full-output costs.
- 3: Report distinguishes hand-derived, cross-implementation, property, and measured evidence and names residual risks.
- 2: Honest limitations, justified next step, authorship/tool/reference provenance, and explicit learner-evidence validation label.

Expected complexity discussion: direct work is Theta(`N*M`) with Theta(`N+M`) result storage. A suitable sparsity-aware traversal uses multiplication work proportional to `Kx*Kh`, while initialization/materialization of the required output remains Theta(`N+M`); auxiliary/result-space terminology must be explicit. Equivalent precise analysis for the actual implementation is acceptable.

## 4. Benchmark and evidence — 10 points

- 2: Dense and zero-heavy cases are deterministic, motivated, and use identical inputs across implementations.
- 2: Warm-up and at least five raw `perf_counter_ns` observations per implementation; construction and serialization excluded.
- 2: Output agreement is checked before timings are accepted.
- 2: JSON matches measured values and records schema version, command, environment, seed/input shape, nonzero counts, repetitions, and `LEARNER_PRODUCED_UNVALIDATED`.
- 2: Report makes only bounded claims and discusses noise/order effects and a useful follow-up.

Do not award speed credit based on a required winner. Correctness and honest evidence matter; either implementation may measure faster in a particular case.

## 5. Comprehension — 20 points

Award 2 points per response: 1 for the essential result and 1 for sound reasoning/application.

1. Start is `1`, length is `4`, and samples are `(8, 6, 7, 15)` (float equivalents accepted). Starts add; sample tuple positions follow the usual zero-based accumulation.
2. Nonempty representation becomes `(start + 3, same samples)` and `y[n] = x[n-3]`, so features move right by three. Reordering values changes the signal rather than its time origin.
3. Empty has no represented interval and canonical start zero; the represented-zero signal has start `-2`, length three, addressable in-support zeros, and participates in full support-length rules. Trimming destroys those observables.
4. Agreement can preserve a shared indexing, sign, truncation, or oracle defect. Full credit requires an actually independent hand calculation, mathematical property, or examiner oracle capable of detecting the named defect.
5. For shifts `a` and `b`, `conv(shift(x,a), shift(h,b))` equals `shift(conv(x,h), a+b)` under the contract. The proposed non-symmetric, nonzero-shift case and assertion must expose a sign error.
6. Different valid accumulation orders change rounding. Exact equality is suitable for identical representation operations and carefully chosen exactly represented integer-valued cases; tolerance is appropriate for general floating accumulation, with scale-aware justification preferred.
7. Direct Theta(`N*M`) time; sparse multiplication traversal proportional to `Kx*Kh`, plus Theta(`N+M`) full-result initialization/materialization. Result storage is Theta(`N+M`); additional temporary storage must match the submitted design.
8. The observation applies only to those cases/environment. Valid threats include density/size choice, interpreter/platform, timer noise, warm-up/cache effects, run order, background load, allocation, seed, and too few samples. Follow-up should vary a controlled dimension with repeated/interleaved measurements.
9. Accept any three concrete causal chains. Expected themes include bool passing naive integer checks, NaN poisoning equality/metrics, infinity invalidating arithmetic, mutable aliases changing hashed/tested values, and ambiguous empty starts changing downstream support.
10. The website is a locator, and the assignment record is an unresolved category even though its source flag is preserved. Needed evidence includes resolved identity/content, provenance and integrity, access/license status, learner-safety classification, and curricular dependencies. Strongest claim is kickoff unit complete and course still in progress.

## Decision record

The examiner should record category scores, cap applications, command evidence locations, failed cases, and one of:

- `VALIDATED_UNIT_1_COMPLETE_COURSE_IN_PROGRESS`
- `NOT_VALIDATED_INCOMPLETE`
- `NOT_VALIDATED_FAILED`

This file is a scoring specification, not evidence that any decision has occurred.
