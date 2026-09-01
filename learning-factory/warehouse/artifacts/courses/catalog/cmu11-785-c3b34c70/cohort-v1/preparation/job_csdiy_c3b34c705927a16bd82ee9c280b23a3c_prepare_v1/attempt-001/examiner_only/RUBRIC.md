# Independent Examiner Rubric: Tested MLP Kickoff

This rubric is examiner-only. Grade the submitted kickoff artifacts without relying on CMU course-site access. The task specification and fixed dataset are sufficient for evaluation. Do not interpret a learner's prose claim or their own passing tests as independent evidence.

## Decision rule

Score out of 100. A passing unit requires **75 or more**, plus every non-compensable gate below. Record the command outputs, report digest, observed versions, and any examiner-authored test cases used. A pass applies only to `unit_kickoff_01_tested_mlp`; it never establishes completion of CMU 11-785.

Non-compensable gates:

1. The core gradient implementation is analytic and learner-written; no autodiff or deep-learning framework is used.
2. Examiner-run finite-difference checks cover at least one well-scaled entry in `W1`, `b1`, `W2`, and `b2` on an input away from ReLU kinks and agree within a justified numerical tolerance.
3. The documented clean test command exits zero, and deliberately perturbing one gradient causes an appropriate test to fail.
4. The experiment can be regenerated from the recorded command and configuration; all numerical results except runtime repeat.
5. No unavailable official course content is represented as retrieved, completed, or authored by the learner.

If a gate fails, report `NOT_YET_COMPLETE` even when the numeric score is 75 or higher.

## Scored criteria

### 1. Numerical and algorithmic correctness — 30 points

- **8 points:** Forward logits, stable mean negative log likelihood, and the stated weight-only L2 term match an examiner implementation on at least two shapes.
- **16 points:** Gradients for all four tensors match finite differences and have exact expected shapes; batch averaging and regularization scaling are correct.
- **6 points:** Prediction and SGD updates are correct; the implementation rejects invalid learning rates and does not mutate caller-owned parameters.

Award at most 12/30 if any trainable tensor has a materially incorrect gradient. Award zero for the gradient subsection if gradients are supplied by an automatic-differentiation system.

### 2. Verification quality — 25 points

- **12 points:** Deterministic central-difference tests cover all parameter tensors, state epsilon/tolerances, avoid ReLU kinks, and detect an examiner-injected sign or scale defect.
- **5 points:** A meaningful tiny forward case is independently expected rather than calculated by calling the implementation under test.
- **4 points:** Extreme finite inputs exercise numerical stability and assert finite loss and gradients.
- **4 points:** Tests cover invalid labels/shapes, empty batches, non-mutation, deterministic repeatability, and a bounded training integration case.

Do not award the relevant points for assertions that merely restate implementation outputs or for flaky pass/fail thresholds.

### 3. Software-engineering quality — 20 points

- **6 points:** Modules have small responsibilities, public contracts are documented, tensor names/shapes are readable, and validation failures are actionable.
- **5 points:** Setup is reproducible with bounded dependencies; README commands work from a clean process and tests run offline.
- **5 points:** Randomness is injected or explicitly seeded, inputs are not mutated, and generated files/caches are excluded from the submission.
- **4 points:** The reflection identifies a concrete test-caught defect, a plausible remaining risk, and a limitation without overstating assurance.

### 4. Experiment and provenance — 15 points

- **6 points:** All six required runs use the exact dataset, split sizes, seeds, initialization, width, L2 coefficient, update count, and learning rates.
- **4 points:** Machine-readable per-run records include configuration, initial/final objective, evaluation accuracy, runtime, Python/NumPy versions, command, and schema version; JSON contains no non-finite values.
- **3 points:** Regeneration preserves every numerical field except runtime, and aggregates can be recomputed from retained runs.
- **2 points:** Conclusions are tied to observed measurements and explicitly bounded to the small synthetic experiment.

### 5. Comprehension — 10 points

Use the answer guide below. Award partial credit for correct reasoning with minor notation errors; do not require exact wording.

- **3 points:** Correct backpropagation and shape reasoning in Prompt 1.
- **2 points:** Correct floating-point stability and finite-difference reasoning in Prompts 2–3.
- **2 points:** Concrete invariant/broadcasting defect detection in Prompts 4–5.
- **2 points:** Complete reproducibility controls and appropriately bounded interpretation in Prompts 6–7.
- **1 point:** Correct distinction among tests, proof, unit completion, and course completion in Prompt 8.

## Technical answer guide

Let `Z1 = X W1 + b1`, `H1 = ReLU(Z1)`, `Z2 = H1 W2 + b2`, and `P = softmax(Z2)`. If `Y` is the one-hot label matrix, then for a batch of size `B`:

- `dZ2 = (P - Y) / B`, shape `(B, C)`;
- `dW2 = H1.T @ dZ2 + l2 * W2`, shape `(H, C)`;
- `db2 = sum(dZ2, axis=0)`, shape `(C,)`;
- `dH1 = dZ2 @ W2.T`, shape `(B, H)`;
- `dZ1 = dH1 * relu_derivative(Z1)`, shape `(B, H)`;
- `dW1 = X.T @ dZ1 + l2 * W1`, shape `(D, H)`; and
- `db1 = sum(dZ1, axis=0)`, shape `(H,)`.

The learner may choose either common ReLU subgradient convention at exactly zero if it is stated and consistent. Examiner gradient inputs should keep all `Z1` values comfortably away from zero.

A stable implementation subtracts the per-row maximum before exponentiation or uses the equivalent log-sum-exp identity. Direct exponentiation can overflow for large positive logits; probabilities may also round to zero, making a subsequent logarithm infinite. A useful adversarial test shifts or scales logits to large finite values and compares with a stable reference while asserting finite loss and gradients.

Central differences estimate a coordinate derivative as `(f(theta + eps) - f(theta - eps)) / (2 * eps)`. Inputs at a ReLU kink do not have a unique ordinary derivative, while too-small `eps` amplifies subtraction cancellation and floating-point rounding. Tolerance should account for value scale; a combined absolute/relative comparison is acceptable.

Strong invariant answers include valid-label bounds, finite outputs for finite extreme inputs, no mutation, deterministic repeatability, exact gradient key/shape correspondence, and probability normalization if probabilities are exposed. A broadcasting defect is best detected by comparison with finite differences or an independent reference across asymmetric, non-singleton shapes; a loss-decrease test alone can miss it.

Seeds control pseudorandom data draws and initialization only when separate or predictably ordered generators are used. Dependency versions, deterministic operation order, fixed configuration, serialization rules, and stable report ordering require explicit environment and program controls, not merely a seed. Runtime is allowed to vary.

For learning-rate interpretation, accept any conclusion that accurately recomputes the submitted results, discusses variability across three seeds, and stays within the synthetic setup. A follow-up must isolate a named explanation—for example, increasing update count to distinguish slow convergence from a worse attainable solution while holding all other factors fixed.

Passing tests samples selected behaviors and guards regressions; it is not a mathematical proof over all inputs. Independent validation, not learner assertion, promotes the unit. This manager-authored eight-hour kickoff covers neither the unavailable official assignments/materials nor the catalog's full course scope.

## Examiner record

Record one of `COMPLETE` or `NOT_YET_COMPLETE`, the numeric score, each gate outcome, evidence locations, and concise remediation. Preserve failures and logs; do not edit the learner submission while grading it.
