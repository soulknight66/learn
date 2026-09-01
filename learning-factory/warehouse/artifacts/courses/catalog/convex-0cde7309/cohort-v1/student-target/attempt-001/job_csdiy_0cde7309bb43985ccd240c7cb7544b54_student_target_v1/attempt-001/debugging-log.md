# Debugging Log

Provenance: learner-authored record of kickoff experiments only. Validation label:
`LEARNER_SELF_CHECKED`.

This log records observable hypotheses, commands, failures, changes, and lessons. It does not contain
private chain-of-thought.

## Interpreter mismatch

Hypothesis: the repository command `PYTHONPATH=src python3 -m unittest discover -s tests -v` would
exercise the Python 3.11 implementation.

Experiment: ran that command with the workspace's unqualified `python3`.

Observed failure: exit 1. The output referenced Python 3.6 standard-library paths and rejected
`from __future__ import annotations`. Four test modules could not import; CLI subprocess checks then
received exit 1 instead of their intended contract exits.

Change: confirmed and used the provided CPython 3.11.5 interpreter by putting its `bin` directory
first on `PATH`. I did not alter the implementation to support Python 3.6 because the bounded unit
explicitly requires Python 3.11.

Result: the same suite logic ran 28 tests and exited 0 with `OK`.

Lesson: interpreter resolution is part of reproducibility. The README and validation record now
state the version requirement and the exact learner-run environment.

## Evidence-gap audit

Hypothesis: the initial green suite covered the explicit task list, but edge transitions at contract
boundaries might still be untested.

Experiment: compared the tests against each status transition and boundary in the supplied task.

Observed gaps:

- the one-update boundary solve converged in one step, but its test did not constrain the maximum to
  one and therefore did not prove that the final allowed update is checked before exhaustion;
- budget zero was covered in projection but not in the solver, and signed JSON zero could emit
  `-0.0` from the initial allocation;
- non-finite parser behavior covered `NaN` but not the valid JSON number spelling `1e309`; and
- internal-error serialization had an implementation path but no injected-failure test.

Changes:

- set the boundary fixture's maximum to one update;
- added zero-budget and negative-zero solver cases and normalized zero during input conversion and
  projection clipping;
- added a CLI `1e309` case expecting `INVALID_NUMERIC`; and
- injected a private `RuntimeError` at the CLI adapter boundary and asserted exit 1, empty stdout,
  one generic stderr JSON document, and no leaked exception text.

Result: 32 tests ran under CPython 3.11.5 and exited 0 with `OK`.

Lesson: a green suite is evidence only for the assertions it actually makes. Transition boundaries,
serialization channels, and language-runtime quirks need direct cases.

## Numerical and exhaustion separation

Hypothesis: a finite but overflow-prone valid input must take the numerical-failure path before it
can be mistaken for iteration exhaustion.

Experiment: launched the real CLI with budget, weights, and targets near `1e308`.

Observation: exit 4, empty stdout, and exactly the specified `NUMERICAL_FAILURE` error on stderr.
No traceback or non-finite JSON token appeared. A separate ill-conditioned one-update input produced
exit 3 with a finite `MAX_ITERATIONS` result on stdout.

Lesson: validity, numerical evaluability, and convergence are separate state dimensions and require
separate durable evidence.

