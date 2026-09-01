# Study Task: Build a Reproducible Collision-Risk Experiment

## Goal and time box

Build a small Python package that compares an exact collision probability with a Monte Carlo estimate, then explain the result and the engineering decisions. Time-box the work to about **8 hours**. A focused, correct component with clear evidence is preferable to extra features.

## Problem definition

An experiment draws `draws` independent integer bucket identifiers uniformly from `0` through `buckets - 1`, with replacement. A trial has a collision when at least two draws have the same identifier.

Your component must:

1. compute the collision probability from the finite mathematical model without simulation;
2. estimate it using repeated simulated trials;
3. attach a justified 95% uncertainty interval to the estimate;
4. accept an explicit seed and avoid module-global random state;
5. expose the model and simulation as importable functions; and
6. provide a command-line entry point that writes a versioned JSON experiment record.

State every modeling assumption in your report. Handle valid boundary cases deliberately, including no draws, one draw, and more draws than buckets. Reject nonsensical values with clear errors.

## Required repository layout

Submit these learner-created artifacts:

```text
submission/
├── README.md
├── report.md
├── comprehension.md
├── src/
│   └── collision_lab/
│       ├── __init__.py
│       ├── __main__.py
│       ├── model.py
│       └── simulation.py
└── tests/
    └── test_collision_lab.py
```

You may split tests across more files. Do not submit generated caches or environment directories.

## Public behavior

Provide documented importable operations with these responsibilities (the precise function names are your choice):

- an exact calculation accepting `buckets` and `draws` and returning a probability;
- a single-trial collision predicate that accepts an injected random-number generator;
- a simulation accepting `buckets`, `draws`, `trials`, and a seed or injected generator, and returning counts and an estimate; and
- a 95% interval calculation whose method and assumptions are identified in the report and JSON.

The exact calculation must remain meaningful for realistic inputs where a naive factorial conversion or direct subtraction can lose range or precision. Describe your numerical strategy and its limits.

Support this CLI shape (additional documented options are allowed):

```text
python -m collision_lab --buckets M --draws N --trials T --seed S --output result.json
```

The command must fail nonzero for invalid input and must not leave a success-looking output record behind after validation failure.

## Experiment-record contract

Write UTF-8 JSON with these fields and JSON value types:

```json
{
  "schema_version": 1,
  "model": "uniform_with_replacement_collision",
  "parameters": {"buckets": 0, "draws": 0, "trials": 0},
  "seed": 0,
  "collision_count": 0,
  "estimate": 0.0,
  "interval": {"level": 0.95, "method": "documented-method-name", "low": 0.0, "high": 0.0},
  "exact_probability": 0.0
}
```

The zeros above demonstrate types only; they are not a valid completed experiment. Use an atomic replace or another documented safe-write approach so an interrupted run is unlikely to expose a partial JSON document. Given the same parameters, seed, Python implementation, and environment, two runs must produce identical JSON values.

## Required investigation

Run the tool for at least the following matrix, using one recorded nonnegative integer seed and enough trials to discuss sampling error:

| Buckets | Draw counts |
| ---: | --- |
| 365 | 10, 23, 40 |
| 65,536 | 100, 300, 1,000 |

Preserve the JSON records or summarize their complete fields in `report.md`. Do not pick a new seed merely because a result looks better. Discuss whether the exact value lies inside each reported interval and why a miss would or would not establish an implementation defect.

## Test and evidence requirements

Use `unittest`; the validation command must be documented in `README.md` and runnable without network access. Include deterministic tests for:

- input validation and mathematical boundary cases;
- repeatability for the same seed and parameters;
- isolation from module-global random state;
- agreement between two independently expressed exact calculations on a small, safe input range;
- the JSON schema, count/probability invariants, and CLI failure behavior; and
- any statistical assertion you retain, with a written reason its failure risk is controlled.

Do not make the main test suite depend on an unseeded outcome. Keep normal test runtime bounded and report the command and result truthfully.

## Written deliverables

In `report.md`, include:

1. the probability model and derivation;
2. the numerical method used by the exact calculation;
3. the estimator and interval method, including assumptions;
4. a concise table of results for the required matrix;
5. an interpretation that separates sampling variability from implementation error;
6. the reproducibility and safe-output design; and
7. known limitations and one sensible next engineering step.

In `comprehension.md`, answer every question from `COMPREHENSION.md` in your own words. Your answers may refer to your code and experiment records.

## Stop condition

Stop after the required package, tests, experiment evidence, report, and comprehension responses are complete. This is one kickoff unit only; do not claim completion of the cataloged course or unverified official assignments and labs.
