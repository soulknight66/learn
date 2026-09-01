# Debugging log

This log records externally checkable hypotheses, commands, failures, fixes,
and lessons. It does not contain private chain-of-thought.

## 1. File-discovery tool unavailable

- Hypothesis: `rg --files` would identify the learner-safe files without
  reading content.
- Experiment: ran `rg --files` with exclusions for the requested outputs.
- Failure: `/bin/bash: rg: command not found`.
- Resolution: used a depth-bounded filename-only `find`, then read exactly
  `COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`.
- Lesson: optional developer tooling cannot be assumed in a minimal runtime.

## 2. Default Python version mismatch

- Hypothesis: the initial modern-standard-library implementation would run
  under the documented `python3` command.
- Experiment: `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
- Failure: test import stopped at `from __future__ import annotations`; the
  interpreter reported that the future feature was unavailable.
- Diagnostic: `python3 --version` was `3.6.8`; the separately available
  managed runtime was `3.11.5`.
- Resolution: retained the default command as the compatibility target.
  Replaced modern union/generic syntax, `dataclasses`, `Protocol`,
  `NormalDist`, and newer subprocess arguments with Python-3.6 standard
  library equivalents. The required 95% normal quantile is a documented
  constant.
- Lesson: validating with a convenient alternate interpreter would have
  hidden a real handoff failure.

## 3. Wilson boundary roundoff

- Hypothesis: Wilson interval bounds would contain estimates at counts zero,
  half, and all successes.
- Experiment: reran the 12-test suite after the compatibility change.
- Failure: for `0/100`, the computed lower bound was
  `3.469446951953614e-18`, slightly above the estimate `0.0`.
- Diagnosis: the Wilson center and half-width are mathematically equal at
  zero successes but rounded differently in separate floating operations.
- Resolution: return the exact lower endpoint `0.0` for zero successes and
  exact upper endpoint `1.0` for all successes; retain clamping elsewhere.
- Verification: the full suite then ran 12 tests in 0.283 seconds and passed.
- Lesson: range clamping alone does not canonicalize a tiny positive residual
  at a mathematical boundary.

## 4. Fixed-seed matrix

- Hypothesis: all six required cases could be generated reproducibly within a
  bounded runtime using 20,000 trials and the preselected seed `1262020`.
- Experiment: invoked the CLI once for each required bucket/draw pair, writing
  distinct files under `submission/results/`.
- Observation: all six commands exited zero; individual wall times were below
  six seconds when run concurrently. Counts and intervals are retained in the
  JSON records and `submission/report.md`.
- Interpretation: all exact values happened to fall within the reported 95%
  intervals. This is consistency evidence, not proof, and no seed was changed.
