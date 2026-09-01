# Study task: finite signals as reliable software

Preparation label: **learner task, manager-authored, not official EE120 material**.

## Goal and time box

In at most **8 hours**, build a standard-library-only Python module for finite discrete-time signals. Implement the same linear-convolution contract in a direct form and a sparsity-aware form, test them with more than duplicated examples, and report reproducible performance observations.

A suggested budget is 1 hour for the contract and design, 2.5 hours for implementation, 2 hours for tests, 1 hour for measurement, and 1.5 hours for the report and comprehension responses. Stop when the required artifacts are complete. Do not add FFTs, plotting, notebooks, web services, or course-lab work.

## Required submission layout

Create exactly these primary artifacts:

```text
submission/
├── signals.py
├── test_signals.py
├── benchmark.py
├── evidence/
│   └── benchmark.json
├── REPORT.md
└── COMPREHENSION_RESPONSES.md
```

Temporary caches are not submission evidence. Do not include copied course material, solution manuals, credentials, or private data.

## Contract for `signals.py`

Use only the Python 3 standard library. Public functions and classes need type hints and docstrings.

### `FiniteSignal`

Provide an immutable `FiniteSignal` value with these public members:

- `FiniteSignal(start, samples)` constructs a signal whose consecutive samples begin at integer index `start`.
- `.start` is the first represented index.
- `.samples` is an immutable tuple of stored floats.
- `value_at(index)` returns the represented value at an integer index and returns `0.0` outside the represented interval.
- `shift(offset)` returns a new signal following the convention `shift(k)[n] = original[n - k]`.

Contract details:

- Accept `int` or `float` samples, but not booleans; store them as floats.
- Every stored sample must be finite: reject NaN and positive or negative infinity.
- Indices, starts, and offsets must be integers but not booleans.
- Expose no mutable alias to sample storage.
- Preserve represented leading and trailing zeros. For nonempty input, do not trim the sample tuple.
- Canonicalize every empty signal to `start == 0` and `samples == ()`.
- Raise `TypeError` for a wrong type and `ValueError` for a non-finite numeric sample. Document the behavior.

You may use a frozen data class or another design that provides the same observable contract.

### Convolution functions

Provide:

```python
def convolve_direct(x: FiniteSignal, h: FiniteSignal) -> FiniteSignal: ...
def convolve_sparse(x: FiniteSignal, h: FiniteSignal) -> FiniteSignal: ...
```

Both functions compute finite, linear (not circular) convolution and must satisfy the same contract:

- If either operand is empty, return the canonical empty signal.
- Otherwise, the output starts at `x.start + h.start` and stores exactly `len(x.samples) + len(h.samples) - 1` samples, including any boundary zeros.
- Reject operands that are not `FiniteSignal` instances.
- Do not mutate either operand.

`convolve_direct` must visibly implement the ordinary nested traversal over represented samples. `convolve_sparse` must be independently structured to avoid multiplication for exact-zero stored samples. It may still allocate the full contractually required output. Neither implementation may call or alias the other, and neither may use a third-party convolution routine.

## Correctness work in `test_signals.py`

Use `unittest`, a fixed random seed, and no network or third-party package. Tests must be deterministic and comfortably finish on a normal laptop.

Cover all of the following:

1. Construction, immutability, `value_at`, positive and negative indices, and positive and negative shifts.
2. Empty, singleton, represented-zero, negative-start, and unequal-length convolution cases.
3. Every required invalid-input category, including the fact that `bool` is a subclass of `int` in Python.
4. Hand-derived examples that do not compute their expected values by calling either submitted convolution function.
5. Agreement of the two implementations over at least 100 fixed-seed generated pairs spanning empty, dense, and zero-heavy inputs.
6. At least three mathematical properties, with generated data that cannot make each property pass vacuously. Suitable properties include commutativity, the unit impulse identity, shift relationships, support length, and distributivity.
7. Floating-point comparisons with a documented tolerance where exact equality is not justified.

Keep the oracle independent: copying the same indexing logic into tests can reproduce the same defect. In `REPORT.md`, identify which checks use hand-derived results and which use cross-implementation or property evidence.

## Reproducible measurement in `benchmark.py`

Benchmark both convolution functions on at least one dense case and one zero-heavy case. Use deterministic inputs, a fixed seed if randomness is used, the same input objects for both implementations, a warm-up, and at least five recorded repetitions per implementation. Verify output agreement before accepting timings. Do not time input construction or JSON writing.

Write `submission/evidence/benchmark.json` with this minimum structure:

```json
{
  "schema_version": 1,
  "validation_label": "LEARNER_PRODUCED_UNVALIDATED",
  "command": "...",
  "environment": {
    "python_version": "...",
    "platform": "..."
  },
  "timer": "perf_counter_ns",
  "cases": [
    {
      "name": "...",
      "seed": 0,
      "input_lengths": [0, 0],
      "nonzero_counts": [0, 0],
      "repetitions": 5,
      "outputs_agree": true,
      "direct_durations_ns": [],
      "sparse_durations_ns": []
    }
  ]
}
```

Replace placeholders with actual values and arrays of raw integer durations. You may add derived statistics, but retain raw observations. Do not delete an inconvenient result or claim that one implementation is universally faster from these cases.

## `REPORT.md`

In roughly 800–1,200 words, record:

- your representation and validation decisions, including empty and represented-zero signals;
- the mathematical indexing convention and how the API encodes it;
- time and auxiliary-space analysis for both convolution implementations, with named variables;
- the kinds of test evidence you used and what defects that evidence could still miss;
- benchmark command, case rationale, result summary, sources of measurement noise, and the limited claim the data supports;
- known limitations and one justified next engineering step;
- provenance: state that the implementation is yours, list any permitted references or tools actually used, and identify generated evidence as learner-produced and not independently validated.

Do not claim to have completed EE120 or an official EE120 lab.

## Run and reproduce

From the directory containing `submission/`, make these commands work:

```bash
python3 -m unittest discover -s submission -p 'test_*.py' -v
PYTHONPATH=submission python3 submission/benchmark.py
```

Run the tests again after generating benchmark evidence. Then put your numbered answers to [COMPREHENSION.md](COMPREHENSION.md) in `submission/COMPREHENSION_RESPONSES.md`.
