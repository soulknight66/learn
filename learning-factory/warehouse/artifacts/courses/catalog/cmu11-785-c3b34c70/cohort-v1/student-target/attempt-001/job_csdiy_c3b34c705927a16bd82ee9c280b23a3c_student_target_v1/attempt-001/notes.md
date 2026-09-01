# Kickoff unit notes

## Scope and source boundary

I used only `COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md` as course
inputs. I attempted the bounded first unit: a trustworthy NumPy implementation
of one two-layer classifier training step. These notes do not represent
completion of CMU 11-785 or access to its external course materials.

## Mathematical contract

For `X: (B, D)`, the forward path is:

1. `Z1 = X @ W1 + b1`: `(B, H)`
2. `A1 = max(Z1, 0)`: `(B, H)`
3. `Z2 = A1 @ W2 + b2`: `(B, C)`

I chose `ReLU'(0) = 0`. For stability, each row of `Z2` is shifted by its
maximum before exponentiation. The per-example NLL is computed as
`log(sum(exp(shifted))) - shifted[y]`. This avoids `exp(large_positive)` and
does not add the maximum back into the loss.

With `G2 = (softmax(Z2) - one_hot(y))/B`, backpropagation is:

- `dW2 = A1.T @ G2 + l2*W2`; `db2 = sum_rows(G2)`
- `G1 = (G2 @ W2.T) * (Z1 > 0)`
- `dW1 = X.T @ G1 + l2*W1`; `db1 = sum_rows(G1)`

The one division by `B` averages all data gradients. Weight regularization is
not divided by `B`, and biases are not regularized.

## Engineering decisions and hypotheses

- Boundary validation is centralized. Wrong container/dtype errors are
  `TypeError`; semantic value/shape errors are `ValueError`; arithmetic beyond
  finite float64 is `FloatingPointError`.
- Computation converts accepted arrays to local float64 views/copies and never
  writes into caller data. SGD allocates an entirely new parameter mapping.
- Hypothesis: elementwise finite differences will expose a missing mean factor,
  transposition, regularization term, or accidental broadcast even if training
  loss decreases. The test samples every trainable tensor with `h=1e-5` away
  from ReLU kinks.
- Hypothesis: row-max shifting keeps a deliberately wrong-label loss finite for
  logits `+10000/-10000`; the stability test checks the loss and all gradients.
- The experiment isolates data and initialization RNG streams. Both learning
  rates receive clones of the same parameters and the same split for each seed,
  making the comparison paired rather than confounded by fresh draws.
- JSON generation rejects NaN/infinity, sorts keys, omits timestamps, preserves
  raw runs, and replaces the destination atomically. Runtime is the sole
  intentionally variable numeric field.

## Verification outcome

The first test launch found that the default `python3` is unsupported Python
3.6.8. A compatible Python 3.11.5 executable exists, but neither interpreter
has NumPy. A temporary attempt to install pinned NumPy 1.26.4 failed because
the environment cannot reach a package index; the temporary directories were
removed. A Python 3.11 AST parse of all five source/test files succeeded.

Consequently, the numerical suite and fixed experiment remain unexecuted in
this attempt. The report is explicitly labeled `BLOCKED`; it contains no
invented measurements. The implementation is a runnable partial submission
once the pinned wheel is supplied.

## Lessons

The main production lesson was that reproducibility begins before seeding:
interpreter compatibility and dependency availability are part of the
executable contract. A test command is not evidence unless it reaches and runs
the assertions. Failure artifacts should remain explicit and machine-readable
instead of being converted into optimistic completion prose.
