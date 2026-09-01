# Study task: inversion-counting component

## Scenario

A ranking-analysis service needs a small dependency-free component that reports how far an integer sequence is from sorted order. Build the component as a reviewable repository artifact, not as a notebook or an isolated code fragment.

## Required layout

Create these artifacts:

```text
src/inversion_count.py
tests/test_inversion_count.py
tools/benchmark.py
benchmark_results.json
DESIGN.md or DESIGN.tex
README.md
COMPREHENSION_RESPONSES.md
```

Do not commit caches, virtual environments, or generated profiling dumps. A compiled PDF may accompany `DESIGN.tex`, but compilation must not be necessary to read or validate the submission.

## Python API contract

In `src/inversion_count.py`, provide:

```python
def count_inversions(values: Sequence[int]) -> tuple[list[int], int]:
    ...
```

The function must satisfy all of the following:

- Accept any finite sequence of Python integers, including an empty sequence, negative values, and duplicates.
- Return a newly allocated list containing the values in nondecreasing order and the exact number of pairs `(i, j)` for which `i < j` and `values[i] > values[j]`.
- Treat equal values as non-inversions.
- Leave the input sequence unchanged and avoid observable module-level mutable state.
- Run in worst-case `O(n log n)` time using `O(n)` auxiliary space, apart from recursion overhead and the returned list.
- Reject an element that is not an integer with a documented exception from the Python API. State and consistently test how `bool` is treated, because it is a subclass of `int` in Python.
- Use only the Python 3.11 standard library.

Keep the production path free of a quadratic fallback or quadratic validation pass. You may use a slow reference implementation inside tests on small inputs.

## Command-line contract

Running

```bash
PYTHONPATH=src python3 -m inversion_count
```

must read one JSON value from standard input. For a valid JSON array of accepted integers, write one JSON object to standard output with exactly the keys `sorted` and `inversions`, then exit `0`. Do not emit progress messages to standard output.

For malformed JSON, a top-level value that is not an array, or a rejected element, exit `2`, write a concise diagnostic to standard error, write no result to standard output, and do not show a traceback. Document the behavior in `README.md`.

## Test work

Use `unittest` and make the suite runnable with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Include reviewable tests for:

- empty, one-element, already ordered, reverse ordered, duplicate-heavy, and negative-value inputs;
- the returned ordering and exact count;
- preservation of mutable input and creation of a distinct output list;
- the chosen `bool` policy and other rejected elements;
- deterministic generated small cases checked against a clearly test-only quadratic oracle;
- at least one documented metamorphic property;
- command-line success and each failure class, using subprocess-level assertions on exit code and output channels.

Use a fixed and visible seed for generated cases. A test should fail because observable behavior is wrong, not because wall-clock timing varied.

## Design note

In `DESIGN.md` or `DESIGN.tex`, concisely include:

1. the API and error contract;
2. the decomposition of the inversion-counting problem;
3. an invariant for the step that combines subproblem results;
4. a correctness argument covering all inversions exactly once, including duplicates;
5. a worst-case time recurrence and its solution, plus an auxiliary-space analysis;
6. the separation between production code and the test oracle;
7. one engineering tradeoff you considered and one known limitation.

Write this as an argument tied to your implementation. Merely naming a familiar algorithm is not a correctness or complexity justification.

## Reproducible benchmark

`tools/benchmark.py` must generate its own integer inputs with a fixed default seed, accept sizes and repeat count as command-line options, run the production API, and emit machine-readable JSON. It must not import the quadratic test oracle.

Run at least four geometrically increasing sizes with at least three repeats each. Preserve one run as `benchmark_results.json`, including:

- sizes, repeat count, seed, and individual timings;
- Python version and platform information available from the standard library;
- a short explicit label that the data is empirical timing evidence, not a proof of asymptotic complexity.

Do not add a hard pass/fail timing threshold. In the design note, compare the observed scaling with the proved bound and name at least two factors that make small timing studies noisy.

## Reproduction note and final review

In `README.md`, give exact commands for the test suite, one valid CLI run, failure-behavior inspection, and benchmark regeneration. State the supported Python version and that no third-party packages are required.

Before stopping, run the documented commands from a clean working directory, inspect the saved benchmark JSON, and make sure every required artifact is tracked. Put deferred enhancements in a short “Future work” section rather than implementing them now.
