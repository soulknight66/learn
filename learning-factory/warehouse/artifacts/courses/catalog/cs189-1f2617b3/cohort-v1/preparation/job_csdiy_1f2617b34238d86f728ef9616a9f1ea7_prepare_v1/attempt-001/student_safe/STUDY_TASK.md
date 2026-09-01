# Study task: a trustworthy k-nearest-neighbors pipeline

## Goal

Implement a deterministic k-nearest-neighbors (k-NN) classifier, use it in a leakage-resistant train/validation/test experiment, and leave evidence that a second engineer can reproduce and inspect.

Work under `submission/`. Do not use network access, external datasets, or third-party packages.

## Required layout

```text
submission/
├── src/
│   ├── knn.py
│   └── experiment.py
├── tests/
│   └── test_knn.py
├── artifacts/
│   └── experiment.json
├── COMPREHENSION_RESPONSES.md
└── README.md
```

You may add modules and test files, but these paths must remain present.

## 1. Classifier contract

In `src/knn.py`, implement `KNNClassifier(k: int, standardize: bool = True)` with:

- `fit(X, y) -> self`
- `predict(X) -> list[str]`
- read-only fitted values `feature_means_` and `feature_scales_`, each exposed as a tuple

The observable behavior is fixed as follows:

1. `X` is a sequence of rows containing finite real numbers. Rows must have one common, positive dimension. Booleans are not accepted as numbers. `y` contains nonempty string labels, one per row.
2. A training set must be nonempty, `k` must be an integer (not a Boolean), and `1 <= k <= len(X)`. Contract violations raise `ValueError`. Calling `predict` before a successful fit raises `RuntimeError`.
3. `fit` copies all caller-provided data needed by the model. It does not mutate its arguments, and later caller mutation must not alter predictions.
4. With standardization enabled, compute each feature's population mean and population standard deviation from the fit data only. Use scale `1.0` for a zero-variance feature. Store the fitted values in `feature_means_` and `feature_scales_`. With standardization disabled, expose zero means and unit scales of the appropriate dimension.
5. Transform training and query rows with those fitted statistics. Rank neighbors by `(squared Euclidean distance, original training-row index)` and take the first `k`.
6. Vote in this order: largest neighbor count, then smallest sum of squared distances for that label among the selected neighbors, then lexicographically smallest label. This rule must handle exact duplicates and equal-distance cases deterministically.
7. `predict` accepts zero or more query rows. Every query row must have the fitted dimension and finite real values; otherwise it raises `ValueError`. An empty query sequence returns an empty list.

Keep model code free of file I/O and global mutable state.

## 2. Deterministic experiment

In `src/experiment.py`, provide testable functions and a command-line entry point. The default run uses seed `189` and candidate values `1, 3, 5, 9`.

### Synthetic data

Use one local `random.Random(seed)` instance; do not seed or consume module-global random state.

Generate 120 rows labeled `negative`, followed by 120 rows labeled `positive`. For every negative row, draw:

```text
x_signal = rng.gauss(-1.0, 0.8)
x_noise  = rng.gauss(0.0, 50.0)
```

For every positive row, draw the same way except that the signal mean is `1.0`. Store each row as `[x_signal, x_noise]`.

Split without leakage:

1. Keep the two label groups separate and shuffle the negative group, then the positive group, using the same RNG.
2. From each group take the first 72 rows for training, the next 24 for validation, and the final 24 for testing.
3. Combine the corresponding label slices, then shuffle the complete training, validation, and test partitions in that order with the same RNG.

This yields 144 training, 48 validation, and 48 test rows.

### Selection and final evaluation

For each candidate `k`, fit a fresh standardized classifier on the training partition and record validation accuracy. Choose the highest validation accuracy, breaking a tie in favor of the smaller `k`. Do not use test labels for preprocessing, selection, or tie-breaking.

After selection, fit a fresh classifier with the selected `k` on the combined training and validation rows. Evaluate exactly once on the untouched test partition. Record accuracy and a confusion matrix whose actual and predicted label order is `negative`, then `positive`.

### CLI and artifact

The following must work from the unit workspace:

```bash
python3 submission/src/experiment.py \
  --seed 189 \
  --output submission/artifacts/experiment.json
```

The JSON artifact must contain at least:

- `schema_version` equal to `1`;
- provenance identifying the data as synthetic, the generator parameters, and seed;
- exact train, validation, and test counts;
- the ordered candidate list and validation accuracy for each candidate;
- the selected `k` and stated selection rule;
- final test accuracy and the 2-by-2 confusion matrix; and
- the classifier configuration, including standardization and deterministic tie rules.

Serialize using `json.dump(..., sort_keys=True, indent=2)` and append one newline. Do not include a timestamp, absolute path, process ID, or other run-specific value. Two default runs in the same environment must produce byte-identical artifacts.

Invalid CLI arguments must produce a nonzero exit. The runner may create the output's parent directory.

## 3. Automated tests

Use `unittest`; the suite must run with:

```bash
PYTHONPATH=submission/src python3 -m unittest discover -s submission/tests -v
```

Include focused tests for all of these risk areas:

- a small case whose neighbor result can be checked directly;
- equal-distance neighbor ordering and all vote tie-break stages;
- standardization, including a zero-variance feature;
- invalid construction, malformed fit data, malformed query data, and prediction before fit;
- non-mutation and ownership of data passed to `fit`;
- candidate-selection ties choosing the smaller `k`;
- exact split sizes with no row assigned to more than one partition; and
- byte-identical experiment artifacts from two runs with the same arguments.

Tests must use temporary directories for scratch outputs and must not depend on test execution order.

## 4. Engineering note

In `submission/README.md`, document:

- the commands to run tests and regenerate the artifact;
- module boundaries and important invariants;
- where preprocessing is fitted and why;
- time and auxiliary-space complexity of fit and prediction in terms of training rows `n`, features `d`, queries `q`, and `k`;
- why the deterministic ordering rules exist; and
- at least two limitations or production risks of this implementation.

Keep the note concise: roughly 500–900 words.

## 5. Written reasoning

Answer every prompt in `COMPREHENSION.md` in `submission/COMPREHENSION_RESPONSES.md`. Refer to your implementation or evidence where helpful. Do not copy the prompts without answering them.

## Final self-check

From a clean working directory, run the documented test command and regenerate `experiment.json`. Confirm that the task does not rely on downloaded material and that no cache, temporary output, environment secret, or absolute local path appears in `submission/`.
