# Study task: build a dependable sensor conversion CLI

Build a small Python 3.11 package named `sensor_pipeline`. It will read ideal ADC observations from CSV, convert them to sensor resistance, calculate a trailing rolling median, and atomically publish deterministic CSV output.

This is an individual software-engineering exercise. Use only the Python standard library, including `unittest` for tests. Do not fetch course pages, assignment solutions, or other external content; none is needed.

## Submission layout

Create this structure in your submission area:

```text
submission/
  README.md
  DESIGN.md
  pyproject.toml
  src/
    sensor_pipeline/
      __init__.py
      __main__.py
      ... your modules ...
  tests/
    ... unittest test modules ...
```

Also create `COMPREHENSION_RESPONSES.md` beside `README.md`. Do not edit the supplied question file.

Your README must give exact commands that work from `submission/`, including:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m sensor_pipeline INPUT.csv OUTPUT.csv
```

## Required command-line contract

Support this interface:

```text
python3 -m sensor_pipeline INPUT_CSV OUTPUT_CSV \
  [--window N] [--v-ref V] [--adc-max M] [--fixed-ohms R]
```

Defaults are:

- `N = 5`
- `V = 3.3` volts
- `M = 4095` counts
- `R = 10000.0` ohms

Configuration is valid only when:

- `N` is a positive odd integer;
- `V` and `R` are finite and strictly positive; and
- `M` is an integer of at least 2.

Invalid configuration must produce a concise diagnostic on standard error, exit nonzero, and leave the requested output path unchanged.

## Input contract

Input is UTF-8 CSV with the exact header:

```csv
timestamp_ms,adc_count
```

It must contain at least one data row. Each row must contain exactly two base-10 integers. You may trim surrounding whitespace from data fields, but not rename or reorder header fields.

- `timestamp_ms` must be nonnegative and strictly greater than the preceding timestamp.
- `adc_count` must satisfy `0 <= adc_count < M`.
- A count equal to `M` is treated as saturated and invalid because the ideal inverse model is singular there.
- Blank records, extra columns, missing columns, non-integers, decoding errors, and non-finite configuration values are invalid.

For a data error, the diagnostic must identify the one-based file line number. Validate the entire input and configuration before publishing output. On any such error, return nonzero and do not create or modify `OUTPUT_CSV`.

## Transformation contract

Use the topology and equations in `COURSE_BRIEF.md`.

For each accepted row:

1. convert the ADC count to `voltage_v` using the ideal ADC relation;
2. algebraically invert the stated voltage-divider relation to obtain `resistance_ohm`;
3. compute `filtered_resistance_ohm` as the median of the current and preceding raw resistance values in the trailing window, or all values seen so far when fewer than `N` exist; and
4. preserve the input order and original integer fields.

For an even-sized startup prefix, define its median as the arithmetic mean of its two central sorted values. Keep full available precision during calculation. Round only while serializing.

Write UTF-8 CSV with this exact header and column order:

```csv
timestamp_ms,adc_count,voltage_v,resistance_ohm,filtered_resistance_ohm
```

Serialize every floating-point field in fixed-point notation with exactly six digits after the decimal point. Use `\n` record terminators so output is stable across platforms.

Input and output paths must refer to different files. Publish through a temporary file in the output directory followed by an atomic replacement. Clean up your temporary file after a failure. A successful invocation may replace an existing output; an unsuccessful invocation must preserve its prior bytes.

## Internal design requirements

Organize the code so that:

- ideal model conversion is usable without invoking the CLI;
- parsing/serialization is separate from model arithmetic;
- rolling-median logic is testable as a pure transformation;
- expected user/data failures do not print a Python traceback; and
- library code does not call `sys.exit`.

Do not silently skip, reorder, clamp, or deduplicate records. Do not round intermediate values. Avoid broad exception handlers that turn programming defects into misleading “bad input” messages.

In `DESIGN.md`, record:

- the algebra used to invert the divider relation;
- units and topology assumptions;
- validation and error categories;
- the rolling-window invariant and time/space complexity;
- the atomic-publication strategy;
- numeric representation and rounding choices;
- test strategy; and
- limitations of the ideal model.

## Required tests

Write deterministic `unittest` coverage for at least:

- several ordinary conversions checked against independently calculated values;
- zero count and near-saturation count;
- exact saturation and out-of-range counts;
- malformed header, row shape, integer fields, and timestamp ordering;
- configuration boundaries, including even and nonpositive windows;
- startup-prefix medians, full windows, eviction, duplicate values, and an outlier;
- exact output header, order, line endings, and six-place formatting;
- command-line success and nonzero failure behavior; and
- preservation of an existing output file when new input is invalid.

Tests must assert observable values or effects, not merely that code executed.

## Suggested timebox

1. Model, contracts, and design sketch — 60 minutes
2. Pure conversion and median logic — 120 minutes
3. CSV and CLI boundaries — 90 minutes
4. Failure-safe publication — 60 minutes
5. Tests and defect fixing — 120 minutes
6. Documentation and comprehension responses — 90 minutes

Stop after the bounded requirements are met. Features such as hardware access, plotting, asynchronous ingestion, calibration fitting, networking, and third-party dataframes are outside this unit.

## Handoff checklist

Before submitting, run the documented test command from a clean shell, run one valid and one invalid CLI example, inspect the generated bytes, and confirm that all claims in README and DESIGN are supported by code or test evidence. Submit the source, tests, documents, and comprehension responses—not generated caches or external course content.

