# Study Task: From Equations to a Tested MLP Training Step

## Mission

Build a small Python/NumPy library for a two-layer multiclass classifier. Treat the mathematical description as an API contract: make shapes, validation, numerical behavior, reproducibility, and evidence explicit. Do not use PyTorch, TensorFlow, JAX, an automatic-differentiation package, or a high-level neural-network implementation.

Target effort: **8 hours total**, including the comprehension prompts. If the time box expires, submit a runnable partial implementation with failing cases and limitations documented honestly.

## Model contract

Use a batch `X` with shape `(B, D)` and integer labels `y` with shape `(B,)`. There are `H` hidden features and `C` classes. The trainable tensors are:

- `W1`: `(D, H)` and `b1`: `(H,)`
- `W2`: `(H, C)` and `b2`: `(C,)`

The model is an affine layer, elementwise ReLU, and a second affine layer. Its objective is mean multiclass negative log likelihood plus

`(l2 / 2) * (sum(W1**2) + sum(W2**2))`.

Biases are not regularized. Class probabilities and loss must be computed stably for very large finite logits. State and consistently implement a convention for the ReLU derivative at zero.

Your core API must provide behavior equivalent to:

```python
loss_and_gradients(params, X, y, l2=0.0) -> (loss, gradients)
sgd_step(params, gradients, learning_rate) -> updated_params
predict(params, X) -> class_ids
```

The exact module names may differ if the README provides a short mapping. The core functions must not mutate caller-owned input arrays or parameter dictionaries. Reject incompatible shapes, empty batches, non-integer or out-of-range labels, negative `l2`, and nonpositive learning rates with documented exception types. Use analytic gradients in the implementation; finite differences belong only in verification code.

## Work products

Create a compact repository with all of the following:

1. `src/` containing the model, objective, prediction, and SGD implementation.
2. `tests/` containing deterministic automated tests.
3. Dependency metadata that pins or bounds the supported Python and NumPy versions.
4. `README.md` with setup, one clean test command, one experiment command, module layout, API behavior, and known limitations.
5. `reports/experiment.json` containing the experiment schema described below and no `NaN` or infinity values.
6. `reports/reflection.md` with no more than 500 words covering one defect caught by testing, one remaining risk, and what the experiment does and does not establish.
7. `responses/COMPREHENSION_RESPONSES.md` answering every prompt in `COMPREHENSION.md` in your own words.

## Required verification

Use a fixed random seed in every randomized test and ensure the complete suite can run offline. Include at least these cases:

- a hand-computable, tiny forward-loss case;
- central finite-difference checks for sampled entries of **every** trainable tensor, using an input chosen away from ReLU kinks;
- a very-large-logit case in which returned loss and gradients remain finite;
- label and shape validation, including an empty batch;
- a non-mutation check for caller-owned inputs and parameters;
- deterministic repeatability from identical parameters, data, and seed; and
- an integration check showing that training on the fixed synthetic data below reduces the objective, without claiming that this proves general correctness.

Record and justify the finite-difference step size and comparison tolerances in test comments or the README. Tests must fail with a nonzero process exit status when an assertion fails.

## Fixed, bounded experiment

Generate a three-class, two-dimensional dataset with NumPy's `default_rng`. For each class, draw 40 points from an isotropic normal distribution with standard deviation `0.35`, centered respectively at `(-2, -2)`, `(2, -2)`, and `(0, 2)`. Shuffle once per seed and use the first 96 points for training and the remaining 24 for evaluation.

Run exactly these configurations:

- seeds: `11`, `22`, and `33`;
- hidden width: `8`;
- initialization: independent normal weights with standard deviation `0.1` and zero biases;
- full-batch SGD for `100` updates;
- `l2 = 0.001`; and
- learning rates `0.01` and `0.2`.

For each of the six runs, `reports/experiment.json` must record the seed, full configuration, initial and final training objective, final evaluation accuracy, and runtime in whole milliseconds. Also record Python and NumPy versions, the exact experiment command, a schema version, and an aggregate for each learning rate. Keep raw per-run results; do not report only the aggregate. The experiment command must overwrite or deterministically regenerate the report rather than requiring manual edits.

Do not assert in advance which learning rate is better. Interpret only the measurements you actually obtain, and identify the limits of conclusions drawn from this small synthetic dataset.

## Submission check

Before stopping, run the README's clean test command from a fresh process, run the experiment command twice, and confirm that all numerical fields other than runtime are identical. Do not include downloaded course content, credentials, generated environments, caches, or large binary artifacts.
