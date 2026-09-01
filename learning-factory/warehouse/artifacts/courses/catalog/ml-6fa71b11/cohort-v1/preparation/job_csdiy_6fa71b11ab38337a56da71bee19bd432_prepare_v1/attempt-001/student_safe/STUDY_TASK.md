# Study Task: Engineer a Linear Regression Component

## Timebox and goal

Timebox this kickoff to roughly eight hours. Build a deterministic ordinary-linear-regression component trained with full-batch gradient descent, surround it with meaningful tests, and explain the engineering decisions. Favor a narrow, well-supported implementation over extra features.

## Objective

For a design matrix \(X \in \mathbb{R}^{n \times d}\), target vector \(y \in \mathbb{R}^{n}\), weights \(w\), and optional intercept \(b\), minimize

\[
J(w,b)=\frac{1}{n}\sum_{i=1}^{n}(x_i^T w+b-y_i)^2.
\]

Derive the update equations yourself. Use one documented convention consistently for the objective, gradients, and reported loss.

## Required project layout

Submit exactly these learner-authored artifacts (supporting package files such as `__init__.py` are fine):

```text
src/linear_model.py
tests/test_linear_model.py
README.md
COMPREHENSION_RESPONSES.md
```

### Estimator contract

Define `BatchLinearRegressor` in `src/linear_model.py` with this public surface:

```python
BatchLinearRegressor(
    learning_rate=...,
    max_steps=...,
    tolerance=...,
    fit_intercept=True,
)

fit(X, y) -> self
predict(X) -> one-dimensional predictions
```

After a successful fit, expose `coef_`, `intercept_`, `n_iter_`, `loss_history_`, and `converged_`. Document the exact meaning and shape of each attribute.

The implementation must:

- use full-batch gradient descent implemented by you; do not delegate fitting to a library estimator;
- initialize deterministically and produce repeatable results for identical inputs and parameters;
- accept a finite numeric two-dimensional `X` and finite numeric one-dimensional `y` with matching, nonzero sample counts;
- support one or more features and both values of `fit_intercept`;
- reject invalid hyperparameters, malformed shapes, empty data, and NaN or infinite values with clear exceptions;
- reject `predict` before fitting and incompatible prediction shapes;
- avoid mutating caller-owned `X` or `y`; and
- stop no later than `max_steps` while documenting and implementing a meaningful tolerance-based convergence rule.

You may use NumPy for arrays and linear algebra. Do not add regularization, stochastic optimization, feature scaling inside the estimator, persistence, or framework integration in this unit.

### Tests

Use deterministic `unittest` tests. Cover at least:

- a one-feature relationship with an intercept;
- a multi-feature relationship;
- `fit_intercept=False`;
- prediction before fitting and a feature-count mismatch;
- invalid hyperparameters and invalid training data;
- repeatability and non-mutation of inputs;
- consistency among fitted attributes, iteration count, and loss history; and
- behavior on a deliberately poorly scaled data set compared with a scaled version.

Choose tolerances from a stated error argument, not only from the values your implementation happens to emit. A closed-form calculation or a tiny hand-checkable case may be used as an independent test oracle; if you use a library solver only in tests, label it as an oracle and keep it out of the implementation path.

Run the suite from the project root with:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

### Deterministic experiment and README

Construct a small synthetic data set with a fixed literal seed. Run the same learning rule on raw features and on a clearly documented scaled representation. Keep the data split, initial state, and hyperparameters fixed except for any learning-rate adjustment you explicitly justify.

In `README.md`, record:

- environment and exact commands needed to run tests and the experiment;
- the public contract and convergence rule;
- the synthetic-data construction and seed;
- results in a compact table, including iterations, final training loss, and one held-out metric;
- what the comparison does and does not establish;
- time and auxiliary-space complexity in terms of samples \(n\), features \(d\), and executed steps \(k\); and
- at least two implementation failure modes or limitations.

Do not claim production readiness or generalization from this small experiment.

## Finish boundary

When the implementation, tests, README, and response document are present, stop. This completes a submission for this kickoff only. It does not authorize marking the catalog course or specialization complete.
