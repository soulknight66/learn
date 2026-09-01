# Study task: engineer a trustworthy softmax classifier

Document status: **MANAGER-AUTHORED UNIT PROMPT — LEARNER SAFE — NOT YET VALIDATED**

## Goal and timebox

Build a small multiclass linear classifier using only the Python 3 standard library. The numerical core, training loop, tests, command-line entry point, and experiment record must form one coherent system. Timebox the work to **5–9 hours**; record unresolved limitations instead of silently expanding scope.

This is unit `managed_unit_01_engineered_softmax`. It is not an official NYU assignment and does not require the unavailable NYU recordings, slides, or assignments.

## Required repository shape

Create the following in your submission workspace:

```text
src/softmax_lab/__init__.py
src/softmax_lab/core.py
src/softmax_lab/train.py
tests/test_core.py
tests/test_training.py
artifacts/metrics.json
artifacts/comprehension.md
DESIGN.md
README.md
```

You may add focused modules or tests. Do not add third-party runtime or test dependencies.

## Model and public contracts

Represent a model with `C` rows of weights and `D` features per row: `weights[c][d]`. The corresponding bias vector has length `C`. For feature vector `x`, class `c` has a logit equal to its bias plus the dot product of its weight row and `x`.

Expose these functions from `softmax_lab.core`:

```python
def softmax(logits: Sequence[float]) -> list[float]: ...

def cross_entropy_from_logits(
    logits: Sequence[float], label: int
) -> float: ...

def loss_and_gradient(
    weights: Sequence[Sequence[float]],
    bias: Sequence[float],
    examples: Sequence[tuple[Sequence[float], int]],
) -> tuple[float, list[list[float]], list[float]]: ...
```

`loss_and_gradient` returns mean cross-entropy loss, a gradient with the same shape as `weights`, and a gradient with the same shape as `bias`. Implement the analytic gradient yourself. Do not use automatic differentiation.

All three functions must reject malformed shapes, empty required sequences, non-finite numeric inputs, and invalid labels with `ValueError`. They must not mutate caller-owned inputs. Document any additional public types and functions.

Numerical requirements:

- compute softmax through a maximum-shifted exponentiation;
- compute cross-entropy directly from logits using a stable log-sum-exp form, rather than taking the logarithm of a rounded probability;
- return finite results for finite logits such as `[1000.0, 0.0, -1000.0]`; and
- state the floating-point tolerance used by each approximate assertion.

## Training experiment

Include this ordered fixture in the experiment (you may use it in tests as well):

```python
[
    ([-2.0, -1.0], 0), ([-1.5, -2.0], 0),
    ([-2.5, -2.0], 0), ([-2.0, -2.5], 0),
    ([ 2.0, -1.0], 1), ([ 1.5, -2.0], 1),
    ([ 2.5, -2.0], 1), ([ 2.0, -2.5], 1),
    ([ 0.0,  2.0], 2), ([-0.5,  1.5], 2),
    ([ 0.5,  1.5], 2), ([ 0.0,  2.5], 2),
]
```

Implement full-batch gradient descent. Initialize weights using a local `random.Random(seed)` instance with a documented small finite range; initialize biases deterministically. Do not read global random state. Fixed example order is acceptable. Keep functions free of wall-clock time, locale, process ID, absolute paths, and other ambient inputs.

The following command must run from the submission root:

```bash
PYTHONPATH=src python3 -m softmax_lab.train \
  --seed 17 \
  --epochs 200 \
  --learning-rate 0.1 \
  --output artifacts/metrics.json
```

Use `argparse`, reject nonsensical arguments, create only the requested output file, and exit nonzero on failure. Write JSON atomically by creating a sibling temporary file and replacing the target only after serialization succeeds.

`metrics.json` must be deterministic JSON with sorted keys, a trailing newline, and at least these fields:

```text
schema_version                 (integer 1)
unit_id                        (managed_unit_01_engineered_softmax)
seed                           (integer)
epochs                         (integer)
learning_rate                  (finite positive number)
example_count                  (integer)
feature_count                  (integer)
class_count                    (integer)
initial_loss                   (finite number)
final_loss                     (finite number)
training_accuracy              (number from 0 through 1)
dataset_sha256                 (lowercase hexadecimal string)
validation_label               (SELF_CHECKED_NOT_INDEPENDENTLY_VALIDATED)
```

For `dataset_sha256`, hash the UTF-8 bytes of the fixture serialized in its given order by `json.dumps(fixture, separators=(",", ":"), ensure_ascii=True)`. Do not include a timestamp in the deterministic metrics file. A successful configured run must reduce the loss and reach at least `0.90` training accuracy on the fixture; these are smoke checks, not claims about generalization.

## Required verification

Use `unittest`. The following command must discover and pass all tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Your tests must independently cover:

1. probability length, bounds, and sum-to-one within an explicit tolerance;
2. invariance of softmax when the same finite constant is added to every logit;
3. finite softmax and loss behavior for extreme finite logits;
4. a hand-computed small case whose expected value is not generated by the function under test;
5. rejection of empty input, ragged weights, dimension mismatch, invalid labels, and `NaN` or infinity;
6. no mutation of caller-owned lists;
7. a centered finite-difference check of selected weight and bias gradient entries, using a documented step and tolerance;
8. loss decrease after one sufficiently small gradient step on a fixed fixture;
9. byte-identical metrics from two isolated runs with the same arguments; and
10. a negative command-line case that exits nonzero and leaves no completed output artifact.

Run the CLI twice from clean output paths and compare the bytes, not just parsed numbers. Save the final canonical run as `artifacts/metrics.json`.

## Engineering notes

In `DESIGN.md`, explain:

- shapes, invariants, and exception behavior at public boundaries;
- the numerical strategy and remaining floating-point limitations;
- how the gradient check is independent of the analytic implementation;
- sources of nondeterminism you removed or controlled;
- time and auxiliary-space complexity in terms of examples `N`, classes `C`, and features `D`; and
- one change needed before accepting untrusted or large production data.

In `README.md`, provide the exact test and experiment commands, supported Python version, file map, and the expected artifact location. Do not claim course completion or official NYU endorsement.

Answer every prompt in `student_safe/COMPREHENSION.md` in your own `artifacts/comprehension.md`. Do not search for or include examiner material.

## Submission boundary

Submit only source, tests, the two requested Markdown documents, and the deterministic metrics artifact. Do not include environments, caches, downloaded course content, credentials, other learners' work, hidden tests, or examiner files. Passing your own tests is evidence for review, not a final validation decision.

## Provenance

Authored for course `course_4458b9e26be374d399138238c715a1b4` from the supplied CSDIY catalog metadata at commit `adce8e13789dc16aa6d1fbe163e9541736defae4`. No external content was retrieved. Validation label: **PREPARED_NOT_VALIDATED**.
