# Independent Evaluation Rubric: Reliable Bisection Kickoff

Evaluate the submitted artifact, not the learner's claim that it works. Run it offline with the documented command, capture the Julia version and exit status, inspect the implementation, and compare comprehension responses with concrete source and test evidence. This rubric validates only the bounded kickoff unit; it cannot certify completion of MIT 18.330, the catalog's problem sets, or the full course.

## Preconditions and caps

- If the project, core source, or test entry point is absent, the unit is not complete and the score is capped at 30.
- If the documented offline test command cannot execute in the declared supported environment because of the submission, the score is capped at 50.
- If tests use network access, nondeterministic pass/fail conditions, or external packages contrary to the task, the score is capped at 60.
- If the routine can loop without the explicit iteration bound or silently reports convergence after non-finite function evidence, the score is capped at 69.
- Examiner-only criteria or expected reasoning must not be copied into learner-facing artifacts.

## Scored criteria (100 points)

### 1. Contract and result design — 15 points

- 5: `DESIGN.md` specifies accepted inputs, assumptions, tolerance scale, evaluation policy, and observable outcomes without contradictions.
- 6: Callers can distinguish convergence, endpoint root, invalid input, missing bracket, non-finite function evidence, iteration exhaustion, and representation stagnation through types or stable structured fields rather than message parsing.
- 4: Results expose the estimate, final bracket, iteration count, and relevant final function evidence; README usage agrees with the code.

### 2. Numerical reasoning and invariant preservation — 25 points

- 7: Initial bracket checking avoids overflow-prone multiplication and handles signed zero or exact endpoint zero coherently.
- 7: Every loop update preserves endpoint ordering and opposing-sign/root evidence under the documented assumptions. The examiner should manually trace both update branches.
- 6: Midpoint selection handles large finite ranges, including finite opposite-sign extremes, without a spurious non-finite candidate when an appropriate finite midpoint exists.
- 5: The stopping rule implements the documented absolute/relative scale and separately detects the absence of representable interior progress.

### 3. Bounded, robust implementation — 15 points

- 5: Finite endpoints, order, tolerance values, iteration budget, and non-finite function returns are checked at appropriate boundaries.
- 4: The implementation has a clear iteration bound and accurate iteration accounting across early and ordinary returns.
- 3: Function calls are deliberate and cached consistently with the documented evaluation policy.
- 3: Code is modular and readable, avoids hidden I/O/global mutable state/broad catches, and uses concise public documentation.

### 4. Deterministic test evidence — 25 points

- 12: All ten required test groups are present with meaningful assertions; award partial credit by demonstrated group, not by test-set labels.
- 5: Tests assert bracket, outcome, width, finiteness, type, or evaluation-count contracts rather than relying only on a chosen decimal estimate.
- 4: At least one test would catch each of these plausible faults: overflow-prone sign comparison, overflow-prone midpoint arithmetic, false convergence at stagnation, and repeated endpoint evaluation.
- 4: The suite is offline, repeatable, and passes; examiner spot checks or added boundary probes agree with its claims.

### 5. Reproducibility and bounded evidence — 10 points

- 4: `Project.toml`, conventional layout, exact test command, Julia version, and minimal usage make the component reproducible.
- 3: The three-run experiment records the requested fields at meaningfully different scales and is consistent with reruns.
- 3: README and experiment limitations distinguish observed behavior from proof and make no course-completion claim.

### 6. Comprehension — 10 points

Award one point per prompt when the response is technically sound and one additional point for each of prompts 1, 3, 5, 8, and 10 when it cites specific, consistent evidence, up to 10 total. Indicators of sound reasoning include:

- the invariant combines endpoint ordering with zero/opposing-sign evidence and is preserved branch by branch;
- interval width, residual, and forward error are not treated as interchangeable;
- relative scale is stabilized near zero by an explicit absolute term;
- adjacent representable endpoints make further bisection impossible regardless of unused iterations;
- test evidence is framed as support for a bounded contract, not proof for arbitrary discontinuous, stateful, or otherwise nonconforming functions.

## Decision

The kickoff unit is complete only when the score is at least 75, no cap forces it below 75, every required deliverable exists, the test suite passes in the declared environment, and criteria 2 and 4 each receive at least 15 points. Record the test command, exit status, score breakdown, observed evidence, and any failure durably. A passing decision advances only this authored kickoff unit; course status remains incomplete.
