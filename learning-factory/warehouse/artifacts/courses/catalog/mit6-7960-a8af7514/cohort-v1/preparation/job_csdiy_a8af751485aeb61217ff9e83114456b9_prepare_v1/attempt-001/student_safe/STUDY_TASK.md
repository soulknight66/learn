# Study Task: Build a Reliable Softmax Classifier

## Objective

Build a small installable Python package for multiclass linear classification. Implement the mathematics yourself with NumPy, verify the derivatives independently, and produce a deterministic experiment record. The result should look like maintainable scientific software rather than a one-off notebook.

Timebox the work to 6–10 hours. Do not download data or course materials; everything needed to generate the data is specified below.

## Mathematical contract

For a batch `X` with shape `(N, D)`, weights `W` with shape `(D, C)`, and bias `b` with shape `(C,)`, define logits `Z = XW + b`. Use multiclass softmax probabilities and mean negative log-likelihood with integer labels `y` in `[0, C)`. Add L2 regularization as `(l2 / 2) * sum(W**2)`; do not regularize the bias.

Use `float64` for the reference path. Your implementation must remain finite for finite logits with magnitudes around 1,000, and it must reject malformed shapes, non-finite arrays, invalid labels, empty batches, and negative `l2` with clear `ValueError` messages.

Implement at least these public operations (names may be wrapped, but the same contracts must be obvious):

- `softmax(logits) -> probabilities`
- `loss_only(X, y, W, b, l2) -> scalar_loss`
- `loss_and_grad(X, y, W, b, l2) -> (loss, grad_W, grad_b)`
- `predict(X, W, b) -> integer_labels`

Do not use PyTorch, TensorFlow, JAX, autograd, scikit-learn model implementations, or symbolic differentiation. NumPy may be the only numerical runtime dependency.

## Deterministic dataset

Generate the dataset locally with `numpy.random.default_rng(1729)`:

1. In class order, draw 120 two-dimensional samples for each Gaussian center `(-2.0, 0.0)`, `(2.0, 0.0)`, and `(0.0, 2.5)`, using coordinate-wise standard deviation `0.55`.
2. Assign labels `0`, `1`, and `2` in the same order.
3. Concatenate the 360 rows, generate one permutation from the same RNG, and apply it to both samples and labels.
4. Use the first 288 rows for training and the remaining 72 for testing. Do not inspect test labels while choosing implementation or training behavior.

Include the generator in the package and test its shape and repeatability. Do not commit generated binary data.

## Implementation and verification

Use full-batch gradient descent with the following reference run:

- initialize `W` and `b` to zero;
- use 250 parameter-update steps;
- use learning rate `0.2`;
- use `l2 = 0.0001`; and
- evaluate initial loss before the first update and final metrics after the last update.

Write a central finite-difference gradient checker with step `1e-6`. Its numerical path may call `loss_only`, but it must not call or reuse an analytic-gradient result. Check every weight and bias coordinate on a small, non-symmetric batch. Report the maximum scaled error, where each coordinate's scale is `max(1, abs(analytic), abs(numeric))`. The maximum error must be at most `1e-5` for the checked `float64` case.

Use Python's `unittest` or another documented test runner. Tests must cover, at minimum:

- output shapes, probability bounds, and row sums;
- behavior under a constant shift of each logits row;
- finite loss and probabilities for large-magnitude finite logits;
- invalid shapes, labels, non-finite inputs, empty batches, and invalid regularization;
- the independent all-coordinate gradient check;
- identical dataset generation and run records for the same seed and configuration; and
- a lower final training loss than initial training loss.

At least one test should fail against an intentionally naive softmax calculation on an extreme-logit example while passing against your production implementation. Keep any intentionally faulty helper inside test code.

## Reproducible entry point

Provide a command equivalent to:

```text
python -m softmax_lab.train --seed 1729 --steps 250 --learning-rate 0.2 --l2 0.0001 --output artifacts/run.json
```

The command must create its output directory if needed and atomically replace only the requested output file. It must fail with a nonzero exit for invalid arguments or data. Avoid timestamps, elapsed times, absolute paths, and other volatile values in `run.json`.

Record at least:

- the schema version and full configuration;
- dataset sizes and class count;
- initial and final training loss;
- final train and test accuracy;
- maximum gradient-check error;
- the random-number generator family and seed; and
- the relevant Python and NumPy versions.

Serialize keys and numeric values consistently. Two consecutive reference runs in the same environment must produce byte-identical `run.json` files.

## Required repository shape

Submit, at minimum:

```text
pyproject.toml
src/softmax_lab/__init__.py
src/softmax_lab/core.py
src/softmax_lab/data.py
src/softmax_lab/train.py
tests/
artifacts/run.json
REPORT.md
COMPREHENSION_RESPONSES.md
```

`pyproject.toml` must declare the supported Python version, NumPy dependency, package discovery, and test command or test instructions. Keep generated caches, virtual environments, and large binaries out of the submission.

## Report and handoff

In `REPORT.md` (600–900 words), include:

1. the module boundaries and public contracts;
2. the commands for a clean test run and the reference experiment;
3. a compact table of recorded results;
4. the numerical failure case and how your tests expose it;
5. time and space complexity in terms of `N`, `D`, and `C`;
6. what the evidence establishes and what it does not; and
7. one concrete next improvement that stays outside this unit.

Answer every prompt from `COMPREHENSION.md` in `COMPREHENSION_RESPONSES.md`. Tie claims to code, tests, or fields in `artifacts/run.json`. A successful kickoff is evidence for this unit alone; it is not evidence that the full course has been completed.

