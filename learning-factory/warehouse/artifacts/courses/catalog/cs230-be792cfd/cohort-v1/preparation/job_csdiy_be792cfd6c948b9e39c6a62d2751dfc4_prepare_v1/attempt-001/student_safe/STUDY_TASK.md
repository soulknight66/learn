# Study task: build and verify a logistic core

Budget **5–6 focused hours**. Work only on the bounded deliverables below; model training, datasets, framework integration, Kaggle work, and official course assignments are outside this kickoff.

## Deliverables

Create this submission layout:

```text
submission/
├── logistic_core.py
├── tests/
│   └── test_logistic_core.py
├── DESIGN.md
├── EVIDENCE.md
└── RESPONSES.md
```

Use Python's standard library only. The code and tests must run offline with:

```bash
python3 -m unittest discover -s submission/tests -v
```

## Public API

Implement these functions in `submission/logistic_core.py`:

```python
def predict_logit(weights, bias, features):
    """Return one linear logit."""

def sigmoid(logit):
    """Return the numerically stable sigmoid of one finite logit."""

def batch_loss_and_gradient(weights, bias, examples):
    """Return (mean_loss, weight_gradient, bias_gradient)."""
```

An example is a pair `(features, target)`. `weights` and `features` are finite real-number sequences of equal, nonzero length; `bias` and `logit` are finite real numbers; `target` is exactly the integer `0` or `1`; and `examples` is a nonempty sequence. A valid result has a float mean loss, a new gradient list with one entry per weight, and a float bias gradient.

For all public functions:

- reject malformed types, booleans used as numeric values, non-finite values, empty vectors or batches, dimension mismatches, and invalid targets with `TypeError` or `ValueError` as appropriate;
- never rely on `zip` in a way that silently truncates mismatched vectors;
- do not mutate an input sequence;
- keep results finite for valid finite examples that generate logits around `-1000` or `1000`;
- compute batch loss and all gradients as means over the examples.

Document any finer contract choice in the function docstrings and `DESIGN.md`. Do not add hidden global state or network/file-system dependencies to the calculations.

## Work sequence

1. **Specify before coding.** In `DESIGN.md`, write the accepted data shapes, error behavior, averaging convention, and numeric-stability strategy. Draw or describe the computation from inputs to logit, loss, and gradients.
2. **Implement.** Keep validation and calculation responsibilities readable. Prefer small helpers when they remove duplication without obscuring the public API.
3. **Test ordinary behavior.** Derive expected values for at least one nontrivial example independently of the implementation. Test each public function and a multi-example batch.
4. **Test boundaries.** Include positive and negative extreme logits, dimension mismatches, an empty batch, invalid labels, non-finite values, booleans, and input non-mutation.
5. **Check derivatives independently.** In the test code, use central finite differences on a nontrivial batch to approximate every weight derivative and the bias derivative. Compare them to the analytic results with a justified tolerance. The numerical checker must call a loss-only path or extract only the loss; it must not reuse the analytic-gradient formula as its oracle.
6. **Analyze.** In `DESIGN.md`, state time and auxiliary-space complexity using batch size \(n\) and feature count \(d\). Discuss at least two realistic failure modes and how the contract or tests expose them.
7. **Record evidence.** Run the specified command. In `EVIDENCE.md`, record the Python version, platform, exact command, observed test count and result, and any remaining limitation. Paste only output you actually observed.
8. **Respond.** Answer every prompt from `COMPREHENSION.md` in `RESPONSES.md`, preserving the question numbers.

## Submission check

Before handing off, open the files as a reviewer would. Confirm the layout is exact, the test run is repeatable from the directory that contains `submission/`, and every claim in `EVIDENCE.md` can be reproduced. Submission is evidence for examination, not a declaration that the unit or course is complete.

