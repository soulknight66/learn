# Study Task: Engineer a Weighted Interval Scheduler

## Mission

Build a deterministic, well-tested Python component that selects a maximum-value compatible subset of jobs. Treat the behavior below as an interface contract: callers should not need to know which efficient algorithm you chose in order to predict the result.

This is a bounded component exercise. Use only the Python 3 standard library. Do not add a command-line interface, perform network access, or incorporate code or assignment text from the catalog's unverified external links.

## Required submission

Create exactly these learner artifacts:

```text
submission/
├── interval_scheduler.py
├── test_interval_scheduler.py
├── DESIGN.md
└── COMPREHENSION_RESPONSES.md
```

The implementation module must expose this public API:

```python
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class Job:
    job_id: str
    start: int
    finish: int
    value: int

def select_jobs(jobs: Sequence[Job]) -> list[str]:
    """Return the selected job IDs in canonical order."""
```

You may add private helpers, but do not change the public field names, function name, argument list, or return type.

## Behavioral contract

### Input validity

For a valid call:

- `jobs` is a finite sequence of `Job` instances;
- every `job_id` is a nonempty string and IDs are unique;
- `start`, `finish`, and `value` are integers, with booleans rejected even though Python treats `bool` as a subclass of `int`;
- `start < finish`;
- `value >= 0`.

If `jobs` is not a sequence, raise `TypeError`. If any record or field violates the remaining rules, raise `ValueError`. Exact exception messages are not prescribed. Validate the complete input before selecting a schedule, and do not mutate the input sequence or any `Job`.

An empty sequence is valid and returns an empty list.

### Compatibility

A job occupies the half-open interval `[start, finish)`. Two jobs are compatible when their occupied intervals do not overlap. In particular, a job finishing at time `t` is compatible with one starting at `t`.

### Optimization

Return IDs for a compatible subset with maximum total `value`. Values are mathematical integers; do not introduce floating-point arithmetic. A zero-value job may be omitted.

### Canonical order and ties

Canonical job order is ascending Python tuple order by:

```text
(finish, start, job_id)
```

Call the canonically ordered jobs `J1, J2, ..., Jn`. For a selected subset, let `bi` be `1` when `Ji` is selected and `0` otherwise. Among all maximum-value compatible subsets, choose the one whose reverse bit vector

```text
(bn, b(n-1), ..., b1)
```

is lexicographically smallest, with `0 < 1`. Equivalently, at the greatest canonical index on which two optimal subsets differ, prefer the subset that excludes that job. This defines one result independently of the caller's input order.

Return the selected IDs in forward canonical order. For example:

```python
[
    Job("A", 0, 2, 5),
    Job("B", 2, 4, 5),
    Job("C", 0, 4, 10),
]
```

has two value-10 possibilities. Its canonical order is `A, C, B`; the specified reverse-bit comparison selects `C`, so the result is `["C"]` for every permutation of the input.

## Performance boundary

The production implementation must use:

- `O(n log n)` ordering/key comparisons in the worst case; and
- `O(n)` auxiliary algorithm records, excluding the returned list and the immutable input objects.

Do not enumerate subsets in the production function. In `DESIGN.md`, analyze the whole path—including validation, sorting, compatibility lookup, optimization, and reconstruction. Also state how variable-length strings and arbitrary-precision integers qualify a simple unit-cost analysis.

The exhaustive method required below belongs only in the bounded test oracle.

## Test engineering requirements

Use `unittest`; the suite must run with:

```bash
PYTHONPATH=submission python3 -m unittest -v submission/test_interval_scheduler.py
```

Your tests must be deterministic and must include:

- empty, singleton, all-compatible, and all-overlapping cases;
- touching interval endpoints and negative time coordinates;
- zero values and multiple optimal subsets;
- input permutations that exercise the canonical tie rule;
- every invalid-input category in the contract;
- checks that the input sequence is unchanged;
- at least one case where choosing the next locally highest-value job is suboptimal;
- an independent exhaustive oracle that checks every subset for small inputs and implements the exact contract, including ties;
- differential comparison with that oracle on at least 200 valid generated instances of at most 10 jobs, using a fixed, documented pseudorandom seed.

The test oracle must not call `select_jobs`, reuse its private helpers, or duplicate the production optimization logic. Keep generated inputs small enough that the complete suite remains bounded and repeatable.

## Design note

Write `submission/DESIGN.md` for a maintainer. Include these sections:

1. **Contract interpretation** — boundaries, validation, canonicalization, and tie semantics.
2. **Algorithm and invariant** — state meaning, compatibility lookup, decisions, and reconstruction.
3. **Correctness argument** — feasibility, optimal value, and why tie handling produces the prescribed unique subset.
4. **Complexity** — end-to-end time and space, with the cost-model qualification requested above.
5. **Test strategy** — what examples, oracle comparisons, and failure classes establish.
6. **Limitations and change risk** — at least two realistic extensions that would require revisiting the design.

Keep the note concise: roughly 700–1,200 words is sufficient.

## Work sequence

1. Rewrite the contract as preconditions, postconditions, and invariants in your own notes.
2. Work several overlap and tie cases by hand before coding.
3. Design the efficient algorithm and its reconstruction path.
4. Implement validation and the public API.
5. Implement direct unit cases, then write the independent oracle.
6. Run fixed-seed differential tests and diagnose discrepancies; do not weaken a test merely to match the implementation.
7. Finish the design note and answer `COMPREHENSION.md` in the required response file.
8. Run the prescribed command from a clean process and inspect all four deliverables.

Do not add features beyond this boundary. Clear evidence for this small contract is more valuable here than a larger unverified system.

