# Study task: build a trustworthy small linear-system solver

## Outcome and timebox

In about eight focused hours, build and explain a Python 3.11 component that solves a nonempty square system `A x = b` when it has a unique solution and reports other cases through a deliberate error contract. The core elimination must be your own implementation.

Create these files in a `submission/` directory:

- `linear_solver.py` — implementation and public exceptions;
- `test_linear_solver.py` — deterministic `unittest` tests;
- `DESIGN.md` — contract, invariants, complexity, tolerance policy, and limitations;
- `COMPREHENSION_RESPONSES.md` — numbered responses to every prompt in `COMPREHENSION.md`; and
- `REFLECTION.md` — a brief account of one defect or design risk you found and how evidence changed your implementation or tests.

## Public contract

Export this function:

```python
solve(A, b, *, tolerance=None)
```

Your public behavior must be unambiguous and documented:

- Accept a nonempty `n × n` sequence of row sequences and a length-`n` right-hand-side sequence containing finite real numbers.
- Return a newly allocated length-`n` list of finite numeric values for a unique solution.
- Do not mutate `A`, its rows, or `b`.
- Reject malformed, empty, ragged, dimension-mismatched, boolean, non-real, or non-finite inputs with a documented built-in exception type.
- Export `InconsistentSystemError` for a system with no solution.
- Export `NonUniqueSystemError` for a system with more than one solution.
- Accept either `None` or a finite, strictly positive real number for `tolerance`; reject other values.

Exception classes and the function must be importable without performing work or printing output.

## Algorithm constraints

Implement forward elimination with partial pivoting followed by back substitution. Do not call NumPy, SciPy, SymPy, a subprocess, a network service, or another ready-made equation solver for the core work. Standard-library helpers are allowed.

When `tolerance` is `None`, choose and document a deterministic default that accounts for both floating-point precision and input scale. Use the same stated policy consistently when deciding whether a pivot or reduced row is effectively zero. Explain why an absolute constant alone is not scale-neutral.

Document at least these loop-level facts in `DESIGN.md`:

1. what the processed pivot columns guarantee;
2. what row swaps preserve;
3. what remains true about the solution set during elimination; and
4. why back substitution is permitted in the unique-solution path.

Give time and auxiliary-space complexity in terms of `n`. State clearly that partial pivoting and a residual check do not turn this educational implementation into a production numerical library.

## Required verification work

Build deterministic tests using only the standard library. Cover at least:

- several unique systems, including one that requires a row swap at the first pivot;
- a system with negative or non-integral coefficients;
- an inconsistent singular system and a distinct non-unique singular system;
- malformed shapes, mismatched dimensions, empty inputs, booleans, and non-finite values;
- invalid explicit tolerance values;
- the promise that all caller-owned inputs remain unchanged;
- repeated calls that demonstrate no leaked state; and
- a scale-aware residual check for returned solutions.

Use assertions that would fail for a plausible incorrect implementation; merely checking that a call returns is insufficient. Keep test data small enough to inspect and do not use random input unless you also use a fixed seed and document the oracle.

Run from the directory containing `submission/`:

```bash
python3 -m unittest -v submission/test_linear_solver.py
```

Record the exact command and result in `REFLECTION.md`. A written claim cannot substitute for captured test execution in the later validation environment.

## Suggested sequence

1. **Model (60 minutes):** Work through small systems by hand and write the elimination invariants in your own words.
2. **Contract (45 minutes):** Decide validation order, public exceptions, numeric-type policy, mutation policy, and tolerance semantics before coding.
3. **Implement (150 minutes):** Build the solver in small functions while preserving the public contract.
4. **Challenge (120 minutes):** Write failure-first and adversarial tests, then repair defects.
5. **Explain (60 minutes):** Finish `DESIGN.md` and the comprehension responses.
6. **Review (45 minutes):** Run tests from a clean process, inspect the diff, and finish the reflection.

Stop when the bounded deliverables are complete. Do not broaden the component into a general-purpose matrix library.
