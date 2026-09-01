# Study task: deterministic image k-NN

## Goal

Build a small, testable Python package that classifies flattened grayscale-image vectors with brute-force k-nearest neighbors. Treat the public behavior below as an engineering contract. The unit is self-contained: do not depend on network access, an external dataset, or third-party packages.

Work under `submission/` and keep generated caches or environment-specific files out of the deliverables.

## Deliverables

Create this structure:

```text
submission/
├── image_knn/
│   ├── __init__.py
│   ├── model.py
│   └── __main__.py
├── tests/
│   └── test_*.py
├── README.md
├── ENGINEERING_NOTE.md
└── COMPREHENSION_RESPONSES.md
```

You may add focused modules when they improve separation of concerns. Tests must run from the workspace root with:

```bash
PYTHONPATH=submission python3 -m unittest discover -s submission/tests -v
```

## Public model contract

Export `KNNClassifier` from `image_knn`. Its public lifecycle is:

```python
model = KNNClassifier(k=3)
model.fit(train_features, train_labels)
predictions = model.predict(query_features)
```

Implement the following behavior:

1. `k` is an integer greater than zero. Boolean values are not accepted as integers.
2. Feature collections contain rows of finite real numbers. Training data is nonempty, every row has the same positive dimension, and the number of labels equals the number of rows.
3. Training labels are nonempty strings.
4. `fit` copies the validated training data and returns the classifier itself. Later mutation of caller-owned lists must not change predictions.
5. A query row must have the fitted feature dimension. An empty query collection is valid and produces `[]`.
6. Calling `predict` before a successful `fit`, or predicting when `k` exceeds the number of fitted rows, fails with a clear exception.
7. Distance is squared Euclidean distance. For a query vector `q` and training vector `x`, use the sum of `(q[i] - x[i]) ** 2` across dimensions. A square root is unnecessary because it does not change neighbor order.
8. Rank candidate neighbors by `(distance, original_training_index)` and take the first `k`.
9. Choose the label with the largest vote count. Break a vote-count tie by the smallest sum of distances among that label's selected neighbors, then by lexicographically smallest label.
10. `predict` returns one string label per query in input order and does not mutate any caller-owned input.

Use deliberate exception types consistently and document them in `README.md`. Do not print from the model API.

## Command-line contract

Support this invocation:

```bash
PYTHONPATH=submission python3 -m image_knn --input request.json
```

The UTF-8 JSON request has this shape:

```json
{
  "k": 1,
  "train": {
    "features": [[0.0, 0.0], [1.0, 1.0]],
    "labels": ["dark", "light"]
  },
  "query": {
    "features": [[0.1, 0.2]]
  }
}
```

On success, write one JSON object to standard output and nothing else:

```json
{"k": 1, "predictions": ["dark"]}
```

Serialize with sorted object keys and end the output with one newline. Repeated runs against the same input must be byte-for-byte identical. A malformed request must exit nonzero and emit a concise diagnostic to standard error without emitting a success object.

## Verification work

Write deterministic `unittest` coverage. Include, at minimum:

- an ordinary prediction whose nearest labels are unambiguous;
- equal-distance ordering and both voting tie breakers;
- `k = 1`, `k` equal to the training-set size, and an oversized `k`;
- prediction before fitting;
- empty, ragged, dimension-mismatched, nonnumeric, Boolean, and non-finite feature values;
- empty or mismatched labels;
- proof that mutating training or query lists after calls cannot mutate learned state or returned results; and
- two CLI executions that produce identical output bytes.

Keep fixtures small enough that a reviewer can calculate expected results by hand. Tests must not contact a network or rely on execution order.

## Engineering note

In `ENGINEERING_NOTE.md`, describe:

- module responsibilities and the public boundary;
- invariants checked at construction, fitting, and prediction;
- time and additional-space complexity using `n` training rows, `q` queries, dimension `d`, and neighbor count `k`;
- how deterministic behavior is maintained;
- how you tested without coupling tests to private implementation details; and
- one realistic limitation of this baseline and a clean path to replace the model later.

Keep the note to roughly 500–900 words.

## Comprehension responses

Answer every prompt in `COMPREHENSION.md` in `submission/COMPREHENSION_RESPONSES.md`. Number answers to match the prompts and use your own reasoning. Do not look for or include restricted solutions.

## Final self-check

From the workspace root, run the documented test command and one valid CLI example that you created. Record the exact commands and observed results in `submission/README.md`. Do not claim success merely because the implementation looks complete; preserve the reproducible evidence for validation.
