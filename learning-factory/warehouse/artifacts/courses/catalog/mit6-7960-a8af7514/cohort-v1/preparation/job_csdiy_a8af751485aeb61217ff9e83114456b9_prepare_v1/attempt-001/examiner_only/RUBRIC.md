# Independent Examiner Rubric — Reliable Softmax Kickoff

This file is examiner-only. Evaluate the learner's submitted artifacts directly; do not infer completion from the learner's prose, and do not copy this material into learner-facing exports. The catalog's unavailable lectures, readings, and assignments are not required for this unit.

## Decision rule

Score out of 100. Mark the unit successful only when the submission earns at least 75 points **and** passes every critical gate below. A successful decision applies only to `kickoff_01_reliable_softmax`; the course remains `IN_PROGRESS`.

Critical gates:

1. A clean, documented command runs the automated tests successfully.
2. The production loss/probability path stays finite on finite logits of magnitude about 1,000, and the required extreme-logit regression test distinguishes it from a naive test helper.
3. The all-coordinate `float64` gradient check covers both `W` and `b`, uses an analytic-independent numerical path, and reports maximum scaled error no greater than `1e-5`.
4. The reference experiment runs from the documented command, produces all required fields, lowers training loss, and yields byte-identical JSON on two consecutive runs in the same environment.
5. No automatic-differentiation or machine-learning model implementation supplies the core loss, derivatives, prediction, or optimization.
6. All eight comprehension responses are substantive and consistent with the submitted code and evidence.

If execution is impossible because of an examiner environment fault, record the infrastructure failure and do not promote the unit. If it fails because dependencies, paths, or commands were not adequately specified, treat that as a submission defect.

## Scoring

### 1. Mathematical and numerical implementation — 20 points

- 8: The mean cross-entropy, unregularized bias, and `(l2 / 2) * ||W||^2` objective agree across `loss_only` and `loss_and_grad`.
- 5: Shapes, dtypes, prediction behavior, and scalar return values follow explicit contracts.
- 4: The stable computation remains finite on required extreme cases and produces valid row distributions.
- 3: Invalid inputs fail deliberately with useful `ValueError` messages rather than incidental broadcasting or indexing errors.

Award at most 10 here if the regularization convention differs from the task, even if internally consistent. Award zero for a core implementation delegated to a prohibited framework.

### 2. Independent verification and tests — 20 points

- 8: The central-difference checker covers every coordinate of `W` and `b`, uses step `1e-6`, applies the specified scaled-error denominator, and avoids the analytic gradient on its numerical path.
- 7: Tests cover distributions, row-shift behavior, extreme logits, invalid inputs, empty input, non-finite values, regularization, and decreasing training loss.
- 3: Tests are isolated and deterministic, with meaningful assertions rather than smoke checks.
- 2: The intentionally naive implementation exists only in test code and the regression would detect its numerical failure.

Do not award full gradient-check credit when the numerical path merely re-expresses or calls the analytic derivative. Inspect the call graph rather than trusting the reported error.

### 3. Software engineering quality — 20 points

- 5: The `src` package layout, packaging metadata, dependency declaration, and clean-run instructions work.
- 5: Modules have coherent responsibilities and public interfaces; training orchestration is not tangled into the numerical core.
- 4: Validation and error behavior protect boundaries without excessive duplication.
- 3: Names, documentation, and types make shapes and invariants reviewable.
- 3: Output creation is scoped to the requested path, uses an atomic same-directory replacement, and avoids caches, environments, and large generated files in the submission.

### 4. Reproducibility and empirical evidence — 20 points

- 6: Dataset construction exactly follows RNG family, seed, class centers, scale, concatenation, permutation, and 288/72 split requirements.
- 5: The zero initialization, 250 full-batch updates, learning rate, regularization, and evaluation timing match the reference configuration.
- 5: `run.json` is well-formed, includes every requested field, excludes volatile values, and is byte-identical across two consecutive reference runs.
- 4: Recorded values are recomputed by the examiner and agree with the report; losses are finite and final training loss is lower than initial loss.

Unexpectedly weak accuracy is not by itself a critical-gate failure if the implementation is correct and the learner diagnoses it honestly. Fabricated, stale, or irreproducible metrics receive zero for this section.

### 5. Reasoning and evidence boundaries — 20 points

- 4: The report accurately describes architecture, commands, results, a numerical failure case, complexity, limitations, and an appropriately scoped next step.
- 16: The eight comprehension responses earn up to 2 points each using the guidance below.

## Comprehension guidance

1. A complete derivation reaches the equivalent of `dZ = (P - one_hot(y)) / N`, `dW = X.T @ dZ + l2 * W`, and `db = sum_rows(dZ)`, with `X: (N,D)`, `Z/P/dZ: (N,C)`, `W/dW: (D,C)`, and `b/db: (C,)`. Equivalent indexed reasoning is valid.

2. The response should use invariance of softmax under adding/subtracting a per-row constant and connect a row such as `[1000, 1001, 999]` to overflow in direct exponentiation. It should distinguish numerical representation failure from an undefined mathematical distribution.

3. Valid risks include sharing a faulty forward loss, label encoding, regularization convention, parameter flattening/index mapping, or data/shape assumptions. Strong responses explain structural separation and add property checks; merely naming “bugs” earns little credit.

4. Central difference has second-order truncation error versus first-order for forward difference under ordinary smoothness assumptions, but very small steps amplify cancellation and rounding. Full credit requires both sides of the tradeoff, not the slogan that smaller is better.

5. Same-environment determinism should include fixed RNG construction and call order, fixed data/order/initialization/training, stable serialization, and exclusion of time/path noise. Cross-version or cross-platform byte/numeric identity is not established merely by two local runs.

6. Accept distinct, justified hypotheses such as data/label corruption, train/test preprocessing mismatch, optimizer/configuration defects, generalization failure, class mapping errors, or a misleading test. Each must be paired with discriminating evidence rather than a generic request for more testing.

7. A dense full-batch evaluation normally costs `O(NDC)` for the matrix products plus `O(NC)` for softmax/loss and stores logits/probabilities or derivative arrays of `O(NC)` in addition to inputs/parameters. Mini-batching or recomputation is a valid tradeoff when its consequences are explained.

8. Supported claims should remain local—for example, contract behavior on tested inputs, derivative agreement near the checked point, and repeatability of the specified run. Unsupported claims include correctness for all inputs/platforms, neural-network or production readiness, broad generalization, mastery of deep learning, or completion of MIT 6.7960.

For each response, give 2 points for correct reasoning tied to submitted evidence, 1 for a partially correct or weakly supported response, and 0 for missing, contradictory, or materially incorrect reasoning.

## Examiner record

Record the exact test and run commands, environment versions, exit codes, recomputed metrics, JSON digest for each repeat, category scores, gate outcomes, and concise failure evidence. The examiner's durable record—not this rubric or the learner's report—is the completion evidence.

