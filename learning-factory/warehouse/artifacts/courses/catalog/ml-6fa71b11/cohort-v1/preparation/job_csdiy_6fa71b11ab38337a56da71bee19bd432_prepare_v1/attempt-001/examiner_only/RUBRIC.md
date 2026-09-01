# Independent Rubric: Linear Regression Engineering Kickoff

This rubric evaluates only `unit_kickoff_linear_regression_engineering`. It does not certify completion of the catalog course, any Coursera course, or the specialization. Evaluate the learner's submitted code and captured validator output; unavailable official materials are neither required nor acceptable as evidence.

## Evidence protocol

Run in an isolated copy with the learner's declared Python/NumPy dependencies. The worker harness should capture the environment, command, exit status, stdout/stderr, and test results. Inspect source rather than trusting README claims. Examiner prose recommends a result; only the worker-harness validator may promote unit state.

Use the documented command first:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

The examiner may add non-secret temporary tests for the published contract. Do not copy those tests, this rubric, scores, or answer indicators into `student_safe/`.

## Critical conditions

Any of the following blocks a completion recommendation regardless of score:

- the implementation is absent or cannot be imported after a reasonable documented setup;
- fitting delegates to scikit-learn or another estimator instead of learner-written batch gradient descent;
- the learner test command does not complete successfully;
- non-finite input can silently produce a fitted model;
- `fit` mutates caller-owned training arrays; or
- required comprehension responses are absent.

## Scoring (100 points)

### 1. Mathematical and algorithmic correctness — 25

- 10: Objective, gradients, and parameter updates use a single consistent scaling convention; both coefficient and intercept paths are correct.
- 6: Predictions and fitted parameter shapes are correct for one and multiple features, including no-intercept mode.
- 5: Iteration limit, history, iteration count, and tolerance-based stopping agree without off-by-one or stale-state errors.
- 4: Deterministic cases converge to a numerically justified neighborhood of an independent least-squares result.

### 2. API contracts and defensive behavior — 20

- 5: Constructor parameters are validated, with booleans not accidentally accepted as numeric step counts or rates where inappropriate.
- 6: Fit rejects non-2D `X`, non-1D `y`, empty or mismatched samples, zero features, nonnumeric data, and non-finite values clearly.
- 4: Predict rejects unfitted use and mismatched or malformed features while returning a one-dimensional finite result for valid input.
- 3: Inputs are not mutated and learned arrays do not alias caller-owned writable storage.
- 2: Re-fitting replaces state coherently and public attributes are documented.

### 3. Test design and determinism — 20

- 6: Exact or independently computed one- and multi-feature cases exercise coefficient, intercept, and prediction behavior with justified tolerances.
- 4: No-intercept and fitted-state/feature-mismatch behavior are tested.
- 4: Invalid hyperparameters, shapes, empty data, and NaN/infinity are tested.
- 3: Repeatability and input non-mutation are demonstrated.
- 3: Tests check iteration/history invariants and make a controlled raw-versus-scaled comparison without flaky randomness.

### 4. Software engineering quality — 15

- 4: Code is cohesive, readable, and separates validation, fitting, and prediction responsibilities without gratuitous abstraction.
- 4: The public API, fitted attributes, exceptions, convergence semantics, and dependencies are documented accurately.
- 3: Commands run from a clean project root; imports do not rely on an examiner's working-directory accident.
- 2: Numeric arrays use appropriate floating-point handling and intermediate allocations are reasonable.
- 2: Repository contents stay within scope and contain no copied solution, secret, hidden grader, or unavailable official assignment content.

### 5. Experiment and analysis — 10

- 3: Synthetic-data generation, literal seed, split, transformations, and parameters make the comparison reproducible.
- 3: The results table reports iterations, final training loss, and a held-out metric, and its claims match captured runs.
- 2: Complexity analysis correctly accounts for `n`, `d`, executed steps `k`, model state, and retained loss history.
- 2: Limitations and failure modes are concrete; the learner does not make a production or generalization claim from the tiny experiment.

### 6. Comprehension responses — 10

Award up to 1.25 per response using the answer indicators below. Partial credit requires reasoning, not keywords.

1. With residual `r = Xw + b - y`, recognizes `r` has shape `(n,)`, `X.T @ r` has `(d,)`, and derives gradients proportional to `2 X.T r / n` and `2 sum(r) / n` under the stated objective. A consistently rescaled objective/update convention is acceptable.
2. Identifies batch training time `O(knd)`; model/current-vector space normally `O(nd + d)` including stored inputs/working arrays, or `O(d)` auxiliary beyond caller input depending on the implementation; retained scalar loss history adds `O(k)`. Accept a carefully justified allocation-specific bound.
3. Connects scaling to curvature/conditioning: a stable step for a high-curvature direction may be very slow in another. Uses controlled measurements rather than claiming scaling universally improves held-out error.
4. States the implemented rule precisely (for example gradient norm, parameter change, or loss improvement), accounts for tolerance and iteration timing, and gives plausible premature-stop and max-step cases.
5. Identifies independent expected parameters/predictions or a separate least-squares oracle plus invariants such as objective decrease, shapes, state consistency, repeatability, and non-mutation. Low error on training data alone is not treated as proof.
6. Separates learned coefficients/intercept and feature count (plus convergence diagnostics) from predict-time checks of fitted state, two-dimensional shape, feature count, numeric type, and finiteness.
7. Discusses iterative `O(knd)` work and learning-rate/conditioning sensitivity versus factorization-based solvers and their memory/numerical tradeoffs; a matrix inverse is not presented as the preferred direct implementation.
8. Supplies three distinct, testable hypotheses—such as overfitting/split variance, distribution shift, leakage or preprocessing mismatch, outliers/noise, or optimization failure—and proposes checks using training data, a separate validation split, or resampling without tuning on the held-out set.

## Recommendation bands

- 85–100: strong unit evidence;
- 75–84: sufficient unit evidence;
- 60–74: revise targeted gaps;
- below 60: substantial revision required.

A completion recommendation requires at least 75 points and no critical condition. Record category scores, concrete file/test evidence, and any deductions. Even a perfect score changes only this kickoff unit's state.
