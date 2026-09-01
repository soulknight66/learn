# Independent examiner rubric — bounded C kickoff

*Artifact provenance: independently course-manager-authored for this preparation job. Validation label: `EXAMINER_ONLY_RUBRIC_PREPARED_NOT_APPLIED`.*

This rubric applies only to the manager-authored unit `kickoff_c_memory_engineering_v1`. It must not be used to claim completion of an official Duke/Coursera unit or of the full specialization.

## Evaluation protocol

Evaluate the submitted tree, not the learner's claims. Start from a clean checkout. Record the compiler and tool versions, then run `make clean`, `make all`, `make test`, and, when supported, `make sanitize`. Inspect the Git log and compare `DEBUGGING.md` excerpts with commands that can still be reproduced. Valgrind may substitute for sanitizers and vice versa only as allowed by the learner task.

Use additional examiner-owned tests for public API behavior, boundary indices, state preservation, and large-capacity overflow. Do not disclose those tests in learner-facing files. Do not require network access or unavailable official course content.

## Safety gates

A submission cannot pass this unit if any of these conditions holds:

- it does not build as C11 from a clean state;
- ordinary valid API use causes a crash, invalid access, use-after-free, double-free, or definite memory leak;
- a bounds, overflow, or observed allocation failure leaves the vector's public state corrupted;
- the learner submits fabricated tool evidence or copied work without attribution; or
- required comprehension responses are absent.

A safety-gate failure caps the result below 70 even if point totals would otherwise pass. Tool unavailability honestly documented with the permitted substitute is not a failure.

## Scored criteria (100 points)

### 1. API contracts and invariants — 15 points

- 5: Header exactly exposes the required types/signatures and is independently includable.
- 5: README states argument validity, ownership, success/error effects, and failure atomicity for every operation.
- 5: `len <= cap`, null-data/zero-capacity equivalence, and initialized live elements hold at public boundaries; initialization and destruction are idempotent as specified.

### 2. Memory-safe implementation — 25 points

- 6: Capacity grows geometrically and adequate existing capacity is reused.
- 6: Element-count, growth, and byte-size overflow are checked before the unsafe calculation or allocation; overflow returns `IV_ERR_OVERFLOW` without mutation.
- 6: Allocation uses a failure-safe ownership transition; the old allocation and logical contents survive failure.
- 4: Insert/remove preserve order with correct overlap handling and boundary behavior.
- 3: Destruction, private helpers, and const/output-pointer usage follow the contract without global mutable state.

Award no credit for an error path merely described in prose when the implementation contradicts it. A sound overflow argument should guard both capacity growth and representability of `capacity * sizeof(int)` without first performing an overflowing multiplication. A sound reallocation argument keeps the owning pointer unchanged until allocation success is known.

### 3. Deterministic tests — 20 points

- 4: Test harness reports deterministic cases and returns nonzero on failure.
- 8: Required operation/boundary cases are meaningfully asserted, including repeated destruction and insertion/removal at all named positions.
- 4: Failure cases assert preservation of pointer, length, capacity, and live contents where applicable.
- 4: The mixed sequence is checked against a genuinely simpler reference model and crosses growth/movement boundaries.

### 4. Build and dynamic analysis — 15 points

- 5: Required Make targets work from clean state, use C11, and enable at least the required warnings; final build is warning-free.
- 5: Sanitizer or Valgrind evidence covers the complete test executable and reports no relevant errors or definite leaks.
- 5: GDB record contains exact commands, a real temporary defect, an informative state observation, and a plausible fixed revision. Spot-check it against source/history when possible.

### 5. Engineering documentation and Git practice — 10 points

- 4: DESIGN accurately explains invariants, growth/failure behavior, and operation complexity.
- 3: Commands and evidence are concise and reproducible; limitations are honest.
- 3: Commits are ordered, reviewable, and free of generated binaries, secrets, or unrelated artifacts.

### 6. Comprehension — 15 points

Score the ten responses holistically:

- 13–15: Precise, implementation-specific reasoning with correct ownership, overflow, failure atomicity, complexity, and tool distinctions; evidence references are verifiable.
- 10–12: Mostly correct with one or two minor omissions that do not undermine memory reasoning.
- 7–9: Partial understanding; answers are generic or contain a substantive misconception.
- 0–6: Missing, largely incorrect, or inconsistent with the submitted implementation.

Expected concepts include a stack-resident structure pointing to separately owned heap storage; preserving the original owning pointer until growth succeeds; checking representable element and byte counts before arithmetic/allocation; amortized constant push under geometric growth with linear growth events; constant indexed get; linear ordered insert/remove; and the double-free/aliasing hazard of a shallow structure copy. Accept equivalent correct API designs for deep copy or explicit move/transfer.

## Decision

- **Pass:** at least 70/100, no safety-gate failure, and independently reproducible build/test evidence.
- **Revise:** below 70 or any safety-gate failure. Report criteria-specific evidence and required corrections.

Record the numeric result, gate status, commands executed, relevant output hashes or excerpts, and examiner identity in the validator-controlled result. A pass promotes only this kickoff unit; it leaves whole-course status incomplete.
