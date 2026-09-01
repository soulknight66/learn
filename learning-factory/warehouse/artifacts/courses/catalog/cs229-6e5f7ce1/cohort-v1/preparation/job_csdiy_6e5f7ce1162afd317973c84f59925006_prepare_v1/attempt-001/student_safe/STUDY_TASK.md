# Study Task: Engineer a Batch Linear Regressor

Provenance: Course-manager-authored for `managed_unit_001_linear_regression_engineering`; no external course content was retrieved.  
Validation label: `AWAITING_HARNESS_VALIDATION`

## Goal and timebox

In at most **eight hours**, build a deterministic multivariable linear-regression component and the evidence needed to trust it. Keep the implementation focused: ordinary least squares, an optional intercept, and full-batch gradient descent. Do not add regularization, stochastic optimization, persistence, plotting, data downloads, or a command-line application.

## Required interface

Create `src/linear_regression.py` with a class named `BatchLinearRegressor`.

Its constructor must accept:

- `learning_rate` (positive finite float),
- `max_iterations` (positive integer),
- `tolerance` (non-negative finite float), and
- `fit_intercept` (boolean).

Implement these methods and fitted attributes:

- `fit(X, y) -> self`
- `predict(X) -> numpy.ndarray`
- `coef_`: one-dimensional coefficient array of length `n_features`
- `intercept_`: scalar, equal to zero when `fit_intercept=False`
- `n_iter_`: number of updates actually performed
- `loss_history_`: one-dimensional sequence containing the loss after every update

Use float64 calculations and initialize all trainable parameters to zero on every call to `fit`. `fit` must minimize

\[
J(\theta)=\frac{1}{2m}\lVert X\theta-y\rVert_2^2
\]

with vectorized, full-batch gradient updates. Do not call `numpy.linalg.lstsq`, an explicit matrix inverse, or a machine-learning estimator inside `fit`; `numpy.linalg.lstsq` is allowed only as an independent reference in tests.

After each update, record the new loss. Stop at `max_iterations`, or when two consecutive recorded losses satisfy

```text
abs(previous_loss - current_loss)
    <= tolerance * max(1.0, abs(previous_loss))
```

A run with only one recorded loss cannot stop by this convergence rule.

## Contracts to enforce

Both methods must reject non-numeric, non-finite, or incorrectly shaped input with a documented `TypeError` or `ValueError`. `fit` requires a non-empty two-dimensional `X` and a one-dimensional `y` with the same sample count. `predict` requires a non-empty two-dimensional `X` with the fitted feature count and must raise `RuntimeError` if called before a successful fit.

Do not mutate caller-owned `X` or `y`. Repeated fits with identical inputs and settings must yield identical observable fitted state. A failed fit must not leave a newly usable, partly fitted model.

## Required evidence

Create `tests/test_linear_regression.py` using `unittest` or `pytest`. All generated data must use fixed constants or an explicitly seeded generator. Include tests that independently demonstrate:

1. recovery of predictions on a noiseless multifeature problem with a nonzero intercept;
2. agreement of predictions with a `numpy.linalg.lstsq` reference on a fixed, well-conditioned noisy problem;
3. correct behavior with `fit_intercept=False`;
4. loss-history length, finiteness, and consistency with `n_iter_`;
5. deterministic repeat fitting and no mutation of caller inputs;
6. rejection of at least: empty data, shape mismatch, NaN or infinity, invalid hyperparameters, wrong feature count at prediction, and prediction before fitting; and
7. transactional fitted state: after a successful fit, a later invalid `fit` call must not expose partially updated parameters as a successful new fit.

Choose well-conditioned fixtures and settings that let gradient descent converge reliably. State numeric tolerances in each assertion; do not rely on rounded display values or visual inspection.

## Deliverables

Submit exactly these learner artifacts:

- `src/linear_regression.py`
- `tests/test_linear_regression.py`
- `DESIGN.md`
- `COMPREHENSION_RESPONSES.md`

In `DESIGN.md`, record the public contracts, parameter representation, stopping behavior, time and space costs per update, test command, dependency assumptions, and one numerical risk you addressed. Keep it to 700 words or fewer.

In `COMPREHENSION_RESPONSES.md`, answer the questions in `COMPREHENSION.md` in order. Keep the whole response to 900 words or fewer.

Run the complete test suite from a clean process and record the command in `DESIGN.md`. A prose claim that tests pass is not completion evidence; the worker harness and independent examiner will run their own checks.
