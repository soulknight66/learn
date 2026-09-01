# Study Task: Build a Reproducible Tabular-Data Auditor

Artifact provenance: manager-authored from the supplied Data100 catalog metadata; the task uses a synthetic fixture and no retrieved course content.

Validation label: `ASSIGNMENT_SPECIFICATION_UNVALIDATED` — these are learner requirements, not a solution, score report, or completion record.

## Goal and timebox

In about six hours, build a small Python program that reads a fixed-schema CSV file, preserves every data row, normalizes typed values, records validation errors, and atomically writes a deterministic JSON audit. Treat this as a compact production component rather than a notebook exploration.

Use only the Python 3 standard library. Do not fetch data or course material.

## Required workspace layout

Create these deliverables:

```text
src/data_audit.py
tests/test_data_audit.py
fixtures/records.csv
artifacts/audit.json
DECISIONS.md
COMPREHENSION_RESPONSES.md
```

Put the following bytes into `fixtures/records.csv` using UTF-8, LF line endings, and one final newline:

```csv
row_id,city,score,active
r1,Chicago,10.0,true
r2, chicago ,10,TRUE
r3,New York,,false
r4,New York,not_available,false
r5,,7.5,true
r2,Chicago,12.0,true
```

## Input contract

- The header must be exactly `row_id,city,score,active` in that order.
- Parse CSV with the standard-library `csv` module. A physical data row with the wrong number of columns is a structural error.
- Report physical source lines starting at line 2 for the first data row.
- Preserve the raw string value of all four fields for every structurally valid data row.
- Do not silently drop, merge, impute, or select a winner among rows.

Apply these field rules:

- `row_id`: trim surrounding whitespace. An empty result becomes JSON `null` and adds error `{"field": "row_id", "code": "required"}`.
- `city`: trim surrounding whitespace and collapse each run of internal whitespace to one ASCII space. An empty result becomes JSON `null` and adds error `{"field": "city", "code": "required"}`. For a nonempty city, also emit `city_key` as the normalized city passed through `str.casefold()`; retain the cleaned spelling separately as `city`.
- `score`: trim surrounding whitespace. Empty means missing: emit JSON `null` without a validation error. Otherwise accept only a value that Python can parse as a finite float. Emit a JSON number when valid; emit `null` and add `{"field": "score", "code": "invalid_number"}` when invalid or non-finite.
- `active`: trim and case-fold the value. Accept only `true` and `false`, emitting a JSON Boolean. Otherwise emit `null` and add `{"field": "active", "code": "invalid_boolean"}`.

A row is valid exactly when its `errors` list is empty. A repeated non-null `row_id` is a dataset-level issue: preserve all occurrences and list the identifier in `duplicate_ids`, but do not turn repetition into a row-level error. Sort each row's errors by `(field, code)` and sort `duplicate_ids` lexicographically.

## Output contract

Write `artifacts/audit.json` with this shape:

```json
{
  "schema_version": 1,
  "input": {
    "name": "records.csv",
    "sha256": "hex digest of the exact input bytes"
  },
  "summary": {
    "total_rows": 0,
    "valid_rows": 0,
    "invalid_rows": 0
  },
  "duplicate_ids": [],
  "field_stats": {
    "row_id": {"missing": 0},
    "city": {"missing": 0},
    "score": {"missing": 0, "invalid": 0},
    "active": {"invalid": 0}
  },
  "records": [
    {
      "source_line": 0,
      "raw": {
        "row_id": "",
        "city": "",
        "score": "",
        "active": ""
      },
      "normalized": {
        "row_id": null,
        "city": null,
        "city_key": null,
        "score": null,
        "active": null
      },
      "errors": []
    }
  ]
}
```

The zeroes and empty values above illustrate types and structure; compute all values from the fixture. Keep records in source order. Count missing or invalid fields according to the input rules, and ensure `total_rows == valid_rows + invalid_rows`.

Serialize with UTF-8, sorted object keys, two-space indentation, and exactly one final newline. Do not include a wall-clock timestamp, absolute path, random value, or other run-dependent data. Two successful runs on unchanged input must produce byte-identical output.

## Program boundary and failure behavior

The command must be:

```bash
PYTHONPATH=src python3 -m data_audit INPUT_CSV OUTPUT_JSON
```

Return exit code 0 after auditing a structurally valid CSV, even when row-level validation errors are present. For wrong arguments, input/output I/O failure, a non-UTF-8 input, the wrong header, malformed CSV, or a wrong column count:

- return exit code 2;
- write a concise diagnostic to standard error;
- do not emit a traceback for an expected operational error; and
- do not create or replace the requested output.

For successful runs, write a temporary file in the output directory, flush and close it, then use `os.replace` so readers never observe a partial report. Clean up that temporary file on failure.

Keep the importable transformation logic free of printing and process exits. Limit CLI-specific behavior to a small boundary function.

## Tests and design note

Use `unittest` and temporary directories. Include deterministic tests for the fixture and focused cases covering:

- missing versus invalid values;
- whitespace and case normalization;
- duplicate preservation and reporting;
- source-line provenance;
- header and row-shape failures;
- protection of an existing output after a failed run; and
- byte-identical repeated output.

The test command is:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

In `DECISIONS.md`, briefly describe your function boundaries, error representation, duplicate policy, atomic-write strategy, and worst-case time and auxiliary-space complexity in terms of the number of rows and total input characters. State any assumptions rather than expanding the task.

Answer the separate questions in `COMPREHENSION_RESPONSES.md`, numbered to match `student_safe/COMPREHENSION.md`. Do not alter the supplied fixture to make a test pass.

## Stop condition

Stop after the six listed deliverables are complete and the test command passes locally. Do not attempt to retrieve or recreate the rest of Data100. The external validator will decide unit completion independently.
