# Trustworthy Convex Allocation Solver

This repository is a candidate learner submission for the bounded kickoff unit
`unit_kickoff_trustworthy_convex_allocation_v1`. It is not a general optimizer, an official
Stanford assignment, evidence of independent validation, or evidence that EE364A has been
completed.

Provenance: learner-authored offline from `COURSE_BRIEF.md`, `STUDY_TASK.md`, and
`COMPREHENSION.md`; no external course material was used. Current evidence label:
`LEARNER_SELF_CHECKED`.

## Run

Use Python 3.11 and run from the submission root:

```bash
PYTHONPATH=src python3 -m allocation_solver INPUT.json
```

The local default `python3` may not be Python 3.11. Confirm it with `python3 --version` or put a
Python 3.11 installation first on `PATH`.

The input must contain a nonnegative budget, at least one uniquely named item with a positive
weight and finite target, and bounded solver settings. A representative document is:

```json
{
  "budget": 1.0,
  "items": [
    {"id": "api", "weight": 1.0, "target": 0.8},
    {"id": "batch", "weight": 2.0, "target": 0.4},
    {"id": "search", "weight": 4.0, "target": 0.3}
  ],
  "solver": {"tolerance": 1e-9, "max_iterations": 10000}
}
```

Successful and exhausted runs write one compact JSON document to standard output. Invalid input,
numerical failure, and unexpected internal failure write one JSON error document to standard
error and leave standard output empty.

| Exit | Meaning | Output stream |
|---:|---|---|
| 0 | Both residuals meet tolerance (`CONVERGED`) | stdout |
| 1 | Unexpected internal failure | stderr |
| 2 | Invalid invocation or input | stderr |
| 3 | Finite iteration limit reached (`MAX_ITERATIONS`) | stdout |
| 4 | Valid input led to a non-finite numerical result | stderr |

Every normal result carries the SHA-256 of the exact input bytes and the fixed label
`LEARNER_GENERATED_NOT_INDEPENDENTLY_VALIDATED`. Whitespace changes the hash even when it does not
change the parsed model.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

The tests use only the standard library. CLI tests use argument vectors, captured streams, a
bounded timeout, and a separate child process group that is killed on timeout. See
`VALIDATION.md` for the exact learner-run environment and observed results.

## Structure

- `src/allocation_solver/model.py`: immutable input model, layered validation, objective, gradient,
  and stable exceptions.
- `src/allocation_solver/projection.py`: deterministic sort-and-threshold simplex projection.
- `src/allocation_solver/solver.py`: bounded projected-gradient loop and residual computation.
- `src/allocation_solver/cli.py`: file I/O, raw-byte hashing, serialization, streams, and exit codes.
- `tests/`: example, contract, numerical-failure, metamorphic, oracle, and CLI tests.
- `DESIGN.md`, `VALIDATION.md`, and `COMPREHENSION_RESPONSES.md`: design and learner evidence.
- `notes.md`, `debugging-log.md`, and `submission.md`: bounded learning record and handoff.

