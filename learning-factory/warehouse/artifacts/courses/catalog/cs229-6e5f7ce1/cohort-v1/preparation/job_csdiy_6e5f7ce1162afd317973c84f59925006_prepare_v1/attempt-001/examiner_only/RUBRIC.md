# Independent Examiner Rubric: Linear Regression Engineering Kickoff

Provenance: Course-manager-authored from the supplied CSDIY catalog snapshot for `course_6e5f7ce1162afd317973c84f59925006`; independent of learner self-report and not derived from restricted assignments.  
Validation label: `AWAITING_HARNESS_VALIDATION`

## Scope and evidence rule

This rubric evaluates only `managed_unit_001_linear_regression_engineering`. It cannot award CS229 course completion. Score repository evidence and fresh executions, not claims in `DESIGN.md`. Preserve the test output used for the decision.

Before scoring, run the learner suite in a clean process and examiner-owned tests using fixed, well-conditioned fixtures. Do not import or expose private Stanford assignments. Examiner tests may use `numpy.linalg.lstsq` as an independent oracle.

## Hard gates

The unit cannot pass if any of these holds:

- a required learner artifact is missing;
- the implementation delegates fitting to `numpy.linalg.lstsq`, an explicit inverse, or an external ML estimator;
- learner or examiner tests fail or cannot run under the documented dependency assumptions;
- outputs are non-deterministic for identical inputs and settings;
- ordinary valid use produces NaN or infinity;
- restricted course material, an answer key, or examiner rubric content appears in learner-safe work; or
- the submission claims completion beyond this bounded unit.

After all hard gates pass, a score of **75/100** is required for unit completion. Only the worker harness may record the validated state transition.

## Scored criteria

### 1. Mathematical and optimization correctness — 25 points

- **10:** Uses the correct vectorized full-batch gradients for feature coefficients and, when enabled, the intercept.
- **6:** Implements the specified objective, zero initialization, post-update loss history, and exact relative stopping rule.
- **5:** Converges on examiner fixtures and produces predictions within the examiner's declared tolerance of the least-squares oracle.
- **4:** Correctly supports `fit_intercept=False` and exposes coefficient and intercept shapes as specified.

### 2. API and state contracts — 20 points

- **6:** Constructor and public API match the task; fitted attributes have stable documented types and meanings.
- **6:** Shape, emptiness, numeric type, finiteness, hyperparameter, feature-count, and pre-fit checks raise documented exception classes.
- **4:** Caller arrays are not mutated and repeated fits reset state deterministically.
- **4:** Validation and local computation precede commit of fitted attributes, so a failed fit cannot expose partially updated new state.

### 3. Test evidence — 20 points

- **6:** Fixed noiseless and noisy multifeature tests exercise a nonzero intercept and a no-intercept case.
- **5:** A genuinely independent `numpy.linalg.lstsq` oracle is used only in tests, with explicit justified numeric tolerances.
- **5:** Negative tests cover every category enumerated in the task, including the transactional-state case.
- **4:** Tests establish loss-history invariants, determinism, and non-mutation without depending on order or ambient state.

### 4. Numerical and diagnostic quality — 15 points

- **5:** Float64 calculation, finite checks, and well-conditioned deterministic fixtures make failures reproducible.
- **5:** `loss_history_` and `n_iter_` agree exactly; convergence and iteration-limit exits are distinguishable from evidence.
- **5:** The design identifies a real numerical risk and addresses it without hiding failures or silently changing the required objective.

### 5. Software engineering quality — 10 points

- **3:** Names, decomposition, and concise documentation make the mathematical flow reviewable.
- **3:** No unnecessary global state, I/O, network use, hidden randomness, or scope additions are present.
- **2:** `DESIGN.md` accurately records contracts, representation, stop behavior, and a reproducible test command.
- **2:** Reported per-update complexity matches the implementation: normally \(O(mn)\) time and \(O(m+n)\) auxiliary space, excluding stored inputs and loss history; accept an accurately justified implementation-specific bound.

### 6. Comprehension — 10 points

Award credit for accurate, implementation-specific reasoning:

- **2:** Gives \(X^T(Xw + b\mathbf{1}-y)/m\) with consistent shapes; treats the separate intercept gradient as the mean residual and explains the API separation.
- **2:** Connects an excessive learning rate to oscillation or growth/non-finite loss and a small rate to slow improvement, using actual loss or iteration evidence.
- **1:** Explains that the oracle checks the iterative result independently and that calling it inside `fit` would avoid testing gradient descent and create shared-path false confidence.
- **1:** Derives complexity from matrix-vector products rather than asserting it without reference to code.
- **1:** Identifies the submitted deterministic and non-mutation tests and the exact observable state each compares.
- **1:** Requires the invalid second fit to leave the last successfully fitted state intact (or the model explicitly unfitted if that alternative was documented before any successful fit) and describes validate/compute/commit staging.
- **2:** Supplies distinct optimization and implementation hypotheses plus deterministic discriminating checks, such as controlled learning-rate iteration evidence versus recomputing predictions/loss from committed parameters.

## Decision record

Record: harness test command and result, examiner test identifier and result, hard-gate findings, section scores, total, disposition (`PASS_THIS_UNIT`, `REVISE_THIS_UNIT`, or `INVALID_SUBMISSION`), and artifact locations. Do not use `PASS_THIS_UNIT` to change whole-course status.
