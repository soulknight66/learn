# Study Task: From Benchmark to Defensible Claim

*Provenance: course-manager-authored with synthetic instructional data. Validation label: learner-safe kickoff task, pending harness validation; not official CMU content.*

## Scenario

A development team has two implementations of the same graph-processing component: `baseline` and `candidate`. A small benchmark was run on two input families. Your job is to build a reproducible analysis and write only the claim that these observations support.

The table below is synthetic instructional data. It does not report an actual CMU experiment, production benchmark, or published result.

## Constraints

- Timebox the work to about six hours.
- Use Python 3 and the standard library only.
- Do not use network access or external course material; none is needed.
- Treat each `case_id` as a matched pair containing exactly one `baseline` and one `candidate` observation.
- Define paired percent change as

  `100 * (candidate_runtime_ms - baseline_runtime_ms) / baseline_runtime_ms`.

  A negative value therefore means that the candidate took less time in that observed pair.
- Use the ordinary sample median; for an even count, average the two middle values.
- Retain full precision during calculation and round numeric results to two decimal places only when serializing output.

## 1. Write the design note

Before running the completed analyzer, create `DESIGN.md`. Include:

1. one precise research question about the supplied observations;
2. a directional hypothesis and a corresponding null statement;
3. definitions of the observational unit, matched pair, explanatory variable, outcome, and estimand;
4. the target population to which someone might wish to generalize, clearly separated from this supplied sample;
5. at least four threats to validity, including one measurement threat and one sampling or generalization threat;
6. a prospective protocol for a real rerun, covering environment capture, warm-up, repetitions, execution order, and implementation/version identity.

Mark this as a design for the synthetic exercise, not a claim of preregistration.

## 2. Create the input data

Copy the following CSV into `data/benchmark.csv` with the header and all 16 rows:

```csv
case_id,family,n,seed,implementation,runtime_ms
sparse-1000-11,sparse,1000,11,baseline,40
sparse-1000-11,sparse,1000,11,candidate,32
sparse-1000-29,sparse,1000,29,baseline,44
sparse-1000-29,sparse,1000,29,candidate,35
sparse-5000-11,sparse,5000,11,baseline,210
sparse-5000-11,sparse,5000,11,candidate,168
sparse-5000-29,sparse,5000,29,baseline,220
sparse-5000-29,sparse,5000,29,candidate,176
dense-1000-11,dense,1000,11,baseline,90
dense-1000-11,dense,1000,11,candidate,96
dense-1000-29,dense,1000,29,baseline,94
dense-1000-29,dense,1000,29,candidate,99
dense-5000-11,dense,5000,11,baseline,480
dense-5000-11,dense,5000,11,candidate,518
dense-5000-29,dense,5000,29,baseline,500
dense-5000-29,dense,5000,29,candidate,535
```

Do not silently repair, omit, or impute input records.

## 3. Build a deterministic analyzer

Implement `src/analyze.py` with this interface:

```bash
python3 src/analyze.py --input data/benchmark.csv --output artifacts/summary.json
```

The command must:

- parse CSV by column name rather than column position;
- require exactly the columns shown above;
- reject blank identifiers, unknown implementations, non-integer `n` or `seed`, and non-finite or non-positive runtimes;
- require each `case_id` to contain one baseline and one candidate row whose `family`, `n`, and `seed` agree;
- reject duplicate implementation rows and incomplete pairs with a clear message on standard error and a nonzero exit status;
- compute every pair's percent change, then the median overall and within each family;
- compute the SHA-256 digest of the exact input bytes;
- create the output directory when needed and write JSON deterministically, without a wall-clock timestamp or machine-specific absolute path.

Use this logical output shape:

```json
{
  "analysis_version": 1,
  "dataset": {
    "kind": "synthetic_paired_benchmark",
    "pair_count": 0,
    "row_count": 0,
    "sha256": "computed-from-input-bytes"
  },
  "estimand": "median_paired_percent_change",
  "overall": {
    "median_percent_change": 0.0
  },
  "by_family": {
    "family-name": {
      "median_percent_change": 0.0,
      "pair_count": 0
    }
  },
  "pairs": [
    {
      "case_id": "example-id",
      "family": "example-family",
      "percent_change": 0.0
    }
  ],
  "exclusions": []
}
```

The zeroes and example names illustrate types and structure; derive all actual values from the CSV. Sort family keys and pair records by `case_id`. Serialize with stable key ordering, two-space indentation, and a trailing newline. A valid supplied file should have no exclusions; invalid data should fail rather than appear as an exclusion.

## 4. Test the data contract

Create an automated test suite under `tests/`. It must run with:

```bash
python3 -m unittest discover -s tests -v
```

Include tests for:

- the valid supplied dataset and its structural counts;
- input rows in a different order, showing that computed statistics and pair ordering are stable;
- a missing matched observation;
- a duplicate implementation within a case;
- at least one malformed or non-positive runtime.

Tests should invoke public functions or the command-line interface and use temporary paths. They must not depend on network access, the current username, or a pre-existing output file.

## 5. Interpret without overclaiming

Write `REPORT.md` in at most 700 words. Include:

- the question and estimand in plain language;
- the observed overall result and both family-specific results;
- a comparison of the overall pattern with the family-specific patterns;
- one defensible descriptive claim limited to these eight pairs;
- a separate paragraph stating what cannot be concluded about causation, other inputs, other machines, or repeated executions;
- at least three concrete improvements for a real follow-up benchmark.

Do not invent confidence intervals, significance tests, repetitions, randomization, hardware details, or external evidence that the dataset does not contain.

## 6. Record reproduction steps

Create `RUN.md` with:

- the supported Python version or version range;
- exact commands to run the tests and analysis from the submission root;
- a short inventory of generated versus source-controlled artifacts;
- the input provenance label `course-manager-authored synthetic instructional data`;
- confirmation that no external resource is required.

Delete `artifacts/summary.json`, rerun the documented commands in a clean local state, and confirm that the regenerated JSON is byte-for-byte stable across two unchanged runs.

## 7. Respond to the comprehension prompts

Answer the prompts in `COMPREHENSION.md` in a separate file named `COMPREHENSION_RESPONSES.md`. Number each response to match its prompt and use your own reasoning rather than repeating definitions alone.

Your final submission should contain only the requested source, data, documentation, tests, and generated summary. Do not claim that it is an official CMU assignment or that it completes the catalog course.
