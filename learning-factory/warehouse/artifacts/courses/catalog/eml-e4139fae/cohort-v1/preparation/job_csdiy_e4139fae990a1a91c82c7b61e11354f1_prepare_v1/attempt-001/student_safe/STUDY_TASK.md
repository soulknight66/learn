# Study task: build and measure a quantized linear operator

## Outcome and timebox

Produce a small, standard-library-only Python component that quantizes a weight matrix, evaluates a matrix-vector product, tests its contract, and records reproducible measurements. Stop after the required artifacts are complete.

Suggested six-hour budget:

- 30 minutes: read the contract and sketch interfaces;
- 2 hours: implement the component and input validation;
- 75 minutes: build deterministic tests;
- 75 minutes: build and run the benchmark;
- 60 minutes: analyze results and answer the comprehension prompts.

No external course material or network access is needed.

## Required submission layout

Create exactly this top-level submission shape; extra source modules are allowed when justified:

```text
submission/
  quant_kickoff/
    __init__.py
    quantization.py
  tests/
    test_quantization.py
  benchmark.py
  DESIGN.md
  results.json
  COMPREHENSION_RESPONSES.md
```

The following commands must work from the directory containing `submission/`:

```bash
PYTHONPATH=submission python3 -m unittest discover -s submission/tests -v
PYTHONPATH=submission python3 submission/benchmark.py --output submission/results.json
```

Use only the Python 3 standard library. Do not copy an external implementation or fetch course files.

## Functional contract

Expose these functions from `quant_kickoff.quantization`:

```python
quantize_matrix(matrix, bits) -> tuple[quantized_matrix, scale]
matvec(matrix, vector) -> list[float]
quantized_matvec(quantized_matrix, scale, vector) -> list[float]
```

Use nested row-major Python sequences for matrices and a flat sequence for a vector. Returned matrices and vectors must be new lists; none of the functions may mutate an input.

### Quantization rule

Support signed `bits` values of 4 and 8 only. For a nonzero finite matrix, use one symmetric scale for the entire matrix:

```text
qmax = 2^(bits - 1) - 1
scale = max(abs(weight)) / qmax
q = clamp(round(weight / scale), -qmax, qmax)
```

Rounding must choose the nearest integer, with an exact halfway case rounded away from zero. For an all-zero matrix, return integer zeros of the same shape and `scale == 1.0`.

Reject with `ValueError`:

- an unsupported bit width;
- an empty, ragged, or zero-column matrix;
- a Boolean or non-numeric matrix/vector element;
- any NaN or infinity;
- an incompatible vector length;
- a nonpositive or nonfinite scale; or
- a quantized value that is not an integer in the range implied by the caller's represented data.

Because `quantized_matvec` has no `bits` parameter, document in `DESIGN.md` how its public boundary validates integer values and what range information remains the caller's responsibility. Do not silently claim a stronger check than the interface permits.

### Linear operator

For an `R x C` matrix and length-`C` vector, `matvec` returns the `R` row dot products. `quantized_matvec` computes the same operator using each reconstructed weight `scale * q`. It must not materialize an entire dequantized matrix on every call.

## Deterministic test suite

Write focused unit tests for the public contract. Include, at minimum:

- a hand-checkable mixed-sign matrix at both supported widths;
- an exact rounding-tie case;
- an all-zero matrix;
- a one-row and a one-column case;
- agreement between `matvec` and a hand-computed result;
- agreement between `quantized_matvec` and explicit dequantization;
- every specified invalid-input family;
- input non-mutation;
- repeat-call determinism; and
- a seeded property-style loop over multiple small shapes.

Tests must derive expected behavior independently of the production function. A test that merely calls the same helper twice is not an oracle.

## Benchmark and result record

Use `random.Random(65940)`. For each shape `(16, 32)`, `(32, 64)`, and `(64, 128)`, generate one matrix and one input vector from `uniform(-1.0, 1.0)`. Reuse that pair for both 4-bit and 8-bit cases.

Quantize before timing. Compare `matvec` with `quantized_matvec` using:

- `time.perf_counter_ns`;
- at least three untimed warmups per path;
- exactly 15 measured repetitions per path;
- alternating which path runs first on each repetition; and
- the median of the 15 individual durations, not one duration divided by 15.

Timing noise is expected. A quantized path is not required to be faster.

For each case, compute maximum and mean absolute output error. Model serialized weight payload—not Python object memory—as:

```text
float payload bytes = 4 * number_of_weights
quantized payload bytes = ceil(number_of_weights * bits / 8) + 4
```

The added four bytes represent one float32 scale. State clearly in `DESIGN.md` that this is a logical packed-storage model even though the standard-library prototype uses Python objects.

`benchmark.py` must overwrite only the path passed to `--output`, create valid JSON, and fail nonzero with a useful message if it cannot do so. Write keys in stable order and use this schema:

```json
{
  "schema_version": 1,
  "unit_id": "kickoff_u01_quantization_engineering",
  "provenance": {
    "generator": "submission/benchmark.py",
    "seed": 65940,
    "python_version": "record the actual value",
    "platform": "record the actual value",
    "command": "PYTHONPATH=submission python3 submission/benchmark.py --output submission/results.json"
  },
  "validation": {
    "label": "LEARNER_GENERATED_UNVALIDATED"
  },
  "cases": [
    {
      "case_id": "random_16x32_b4",
      "rows": 16,
      "cols": 32,
      "bits": 4,
      "repetitions": 15,
      "float_payload_bytes": 2048,
      "quantized_payload_bytes": 260,
      "max_abs_output_error": "finite nonnegative number",
      "mean_abs_output_error": "finite nonnegative number",
      "float_median_ns": "positive integer",
      "quantized_median_ns": "positive integer"
    }
  ]
}
```

The sample case shows types and naming; `cases` must contain all six shape/width combinations in shape order and then bit-width order. Numeric fields must be JSON numbers, not the explanatory strings shown above.

## Engineering note

In `DESIGN.md`, briefly record:

1. the public API and invariants;
2. validation and rounding decisions;
3. how the tests avoid sharing the implementation's logic;
4. benchmark controls and remaining sources of noise;
5. observed error, payload, and runtime tradeoffs, citing `case_id` values; and
6. the limits of this prototype, including why logical bit count is not proof of process-memory savings or hardware acceleration.

Keep the note evidence-based. Do not claim speed, compression, accuracy, or completion beyond what the artifacts demonstrate.

## Finish line

The unit is ready for external validation when the required commands run, the checked-in `results.json` comes from the checked-in benchmark, all prompts have original responses, and the generated record still says `LEARNER_GENERATED_UNVALIDATED`.

Do not proceed into pruning, architecture search, LLM deployment, or any catalog-described official lab as part of this task. Those are outside this unit's boundary.

---

Provenance: manager-authored kickoff specification based on a quantization topic in the supplied CSDIY catalog snapshot; no official assignment body or external solution was used.
