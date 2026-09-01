# Debugging log

This log records observable hypotheses, commands, outcomes, and fixes. It does
not contain private reasoning or claim checks that did not run.

## 1. Initial clean-suite attempt

Hypothesis: the repository tests would import and begin checking the numerical
core with the workspace's default `python3`.

Command:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Outcome: exit status 1. Both test modules failed during parsing with
`SyntaxError: future feature annotations is not defined`. The traceback showed
the Python 3.6 standard library, so no numerical test executed.

Resolution: version probes established default Python 3.6.8 and an available
Python 3.11.5 at the provided tool path. I made the supported Python interval
explicit (`>=3.10,<3.13`), pinned NumPy, and documented a virtual-environment
interpreter in the test and experiment commands.

## 2. Dependency availability

Hypothesis: NumPy might already be installed for either interpreter.

Experiment: import `platform` and `numpy` under the default and Python 3.11
interpreters.

Outcome: both exited 1 with `ModuleNotFoundError: No module named 'numpy'`.

## 3. Temporary dependency installation

Hypothesis: pinned NumPy 1.26.4 could be installed into a temporary,
workspace-local target without altering system state.

Experiment: created `.test-deps` and `.pip-cache`, then invoked Python 3.11 pip
with `--target .test-deps` and `numpy==1.26.4`.

Outcome: exit status 1 after bounded retries. DNS/package-index access was
unavailable, so pip found no candidate. Both temporary directories were then
removed explicitly; they are not submission artifacts.

## 4. Existing-package fallback

Hypothesis: an existing NumPy directory or cached wheel might permit an offline
run.

Experiment: searched only standard system-library paths and the supplied
Python 3.11 tree for a directory/name matching NumPy, queried installed RPMs,
and asked pip only for NumPy cache entries.

Outcome: no installation, RPM, or cached wheel was found. No further package
or unrelated filesystem search was performed.

## 5. Static syntax check

Hypothesis: despite the unavailable runtime dependency, Python 3.11 could parse
all authored source and test modules without writing bytecode.

Experiment: loaded every `*.py` under `src/` and `tests/` and passed its text to
`ast.parse` using Python 3.11.5.

Outcome: exit status 0; five Python files parsed.

## Unresolved verification

- The 10 numerical/integration tests have not executed.
- The six experiment runs and second-run determinism comparison have not
  executed.
- `reports/experiment.json` is therefore a blocked configuration record, not a
  result report.

Next experiment: provide the pinned NumPy 1.26.4 wheel, run the README clean
test command, run the experiment command twice, and recursively compare both
reports after removing only each run's `runtime_ms`.
