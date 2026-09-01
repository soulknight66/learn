# Independent examiner rubric — Unit 01

This file is examiner-only. It contains scoring criteria and reference results that must not be copied into learner-safe materials.

## Scope and examination procedure

Evaluate only the manager-authored kickoff, **Reliable Logistic Core: From Equation to Tested Python**. Do not infer access to Coursera content and do not award official-course or whole-course completion. The learner's prose and captured output are claims to verify, not proof by themselves.

1. Confirm the five required submission files are present.
2. From the directory containing `submission/`, record the interpreter version and run `python3 -m unittest discover -s submission/tests -v` with network access unnecessary.
3. Inspect the implementation and tests. Add independent spot checks when learner tests do not establish a criterion.
4. Score each section, apply caps, then apply the completion gate.

## Reference results

For one example, the expected definitions are:

\[
z = b + \sum_j w_j x_j,
\qquad p = \sigma(z),
\]

\[
\ell(z,y) = \max(z,0) - yz + \log(1 + e^{-|z|}),
\]

with a stable branch for sigmoid. For a batch of size \(n\), the required mean derivatives are:

\[
\frac{\partial L}{\partial w_j} = \frac{1}{n}\sum_i(\sigma(z_i)-y_i)x_{ij},
\qquad
\frac{\partial L}{\partial b} = \frac{1}{n}\sum_i(\sigma(z_i)-y_i).
\]

A central-difference oracle for parameter \(\theta\) is

\[
\frac{L(\theta+h)-L(\theta-h)}{2h}.
\]

Equivalent stable formulas are acceptable. Values need not be bit-identical, but ordinary cases must agree within a justified floating-point tolerance and valid logits around \(\pm1000\) must not raise overflow errors or yield NaN/infinity.

## Scoring

### A. Public API and executable baseline — 15 points

- 5: All three named functions exist with the required return shapes and no third-party dependency.
- 5: The required command discovers meaningful tests and exits successfully.
- 5: Code is import-safe, deterministic, offline, and free of calculation-time file/global-state side effects.

### B. Mathematical correctness and stability — 25 points

- 6: Logit and sigmoid are correct on ordinary inputs.
- 7: Mean binary loss is correct on single- and multi-example inputs.
- 7: Every mean weight derivative and the mean bias derivative are correct.
- 5: Stable behavior is demonstrated for both signs at large magnitude without undocumented clipping.

### C. Contract safety — 15 points

- 3: Empty vectors/batches and dimension mismatches are rejected before calculation.
- 3: Targets other than the exact integers 0 and 1 are rejected.
- 3: Booleans and malformed non-real inputs are rejected consistently.
- 3: NaN and infinities are rejected consistently.
- 3: Caller-owned inputs are not mutated, and mismatched sequences cannot be silently truncated.

### D. Verification quality — 20 points

- 5: Ordinary cases use independently derived expected values and meaningful assertions.
- 5: Tests cover both extreme signs plus the required invalid-input classes.
- 7: Central differences check every weight and the bias on a nontrivial batch without reusing the analytic-gradient expression.
- 3: Step size and tolerance are justified and tests would fail after a plausible gradient defect such as omitting batch averaging.

### E. Software-engineering analysis and evidence — 15 points

- 4: Responsibilities, names, docstrings, and validation flow make the code reviewable.
- 3: `DESIGN.md` states a coherent contract and stability strategy matching the code.
- 3: Complexity is correctly identified as \(O(nd)\) time and \(O(d)\) returned/accumulator space, excluding inputs (or an accurately justified equivalent for the implementation).
- 2: At least two concrete failure modes are linked to prevention or detection.
- 3: `EVIDENCE.md` contains an honest, reproducible environment/command/result record and discloses limitations.

### F. Comprehension — 10 points

Award credit across all eight responses for these expected ideas:

- invariants are identified and tied to actual enforcement points;
- direct exponent/log probability calculations can overflow, underflow, round to 0 or 1, or attempt `log(0)`, while stable logit-space algebra avoids those failure paths;
- inconsistent sum/mean scaling changes the gradient by batch size and is exposed by a multi-example numeric or exact-value test;
- gradient checks test local derivatives directly, while a one-step loss decrease is weak and step size/cancellation/tolerance can mislead finite differences;
- `zip` truncates silently, so explicit length validation and a mismatch test are needed;
- complexity reasoning is connected to traversing all \(nd\) feature values and retaining a length-\(d\) gradient;
- a locator is not content, content is not validated completion, and this unofficial 6-hour kickoff cannot complete an approximately 80-hour catalog course;
- reproducible execution facts are distinguished from qualitative claims that require code/test inspection.

Score 0–10 by completeness, correctness, specificity, and consistency with the submitted work. Do not require the reference wording.

## Caps and critical defects

- If learner-caused import or execution failure prevents substantive examination, cap the total at 25.
- If loss or gradient calculation is missing, cap the total at 45.
- If ordinary calculations work but extreme valid inputs overflow or become non-finite, section B receives at most 18 and the critical defect remains unresolved.
- If no independent derivative check exists, section D receives at most 10.
- If tests contain no meaningful assertions, section D receives at most 5.
- Unsupported or fabricated evidence earns 0 for the evidence item and must be flagged; independently observed behavior may still earn its own points.
- Use of a third-party numeric or ML package earns 0 for the relevant API item and must be removed before validation because the unit contract requires the standard library.

## Unit completion decision

Record `UNIT_01_VALIDATED` only when all conditions hold:

- total score is at least 80/100;
- section B is at least 18/25;
- section C is at least 9/15;
- section D is at least 12/20;
- the examiner-observed test run succeeds; and
- no critical defect above remains unresolved.

Otherwise record the unit as not yet validated and preserve the score, evidence, and actionable findings for a later attempt. Even `UNIT_01_VALIDATED` advances the course only to `IN_PROGRESS`; it is never evidence of whole-course completion.
