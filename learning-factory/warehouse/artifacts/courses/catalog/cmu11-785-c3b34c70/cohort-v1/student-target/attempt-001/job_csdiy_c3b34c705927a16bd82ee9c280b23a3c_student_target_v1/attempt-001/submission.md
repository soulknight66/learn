# Bounded kickoff submission

Status: **partial and dependency-blocked**. This submission attempts only the
self-contained first unit. It makes no whole-course completion claim.

## Delivered

- `src/tested_mlp/`: validated, stable analytic MLP objective, gradients,
  prediction, nonmutating SGD, and deterministic report generator.
- `tests/`: deterministic hand calculation, finite differences for every
  tensor, extreme logits, API validation, non-mutation, repeatability, training
  integration, and report-repeatability checks.
- `pyproject.toml` and `requirements.txt`: Python bounds and exact NumPy pin.
- `README.md`: setup, one clean test command, experiment command, API contract,
  tolerances, layout, and limitations.
- `responses/COMPREHENSION_RESPONSES.md`: responses to all eight prompts.
- `reports/reflection.md`: bounded reflection under 500 words.
- `notes.md` and `debugging-log.md`: derivation, engineering decisions, concrete
  experiments, failures, and lessons.
- `reports/experiment.json`: an explicitly `BLOCKED` configuration artifact;
  it is not presented as measured evidence.

## Evidence and limitation

Python 3.11.5 successfully parsed all five authored Python modules. The first
clean test attempt failed before assertions because the default Python is 3.6.8.
The compatible interpreter then failed to import NumPy, and a temporary pinned
install failed because package-network access is unavailable. Temporary
dependency/cache directories were removed.

Accordingly, I did not claim a passing suite, did not fabricate experiment
metrics, and did not interpret nonexistent aggregates. The required test run,
two experiment runs, and equality check excluding runtime remain outstanding.
With NumPy 1.26.4 available, the exact commands to resume are:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m tested_mlp.experiment --output reports/experiment.json
```

The second experiment invocation should overwrite the report; compare all
fields except `runs[*].runtime_ms`. Independent validation is still required.
