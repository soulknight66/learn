# Revision Debugging Log

Provenance: fresh learner-authored record of observable experiments in this kickoff workspace.
Validation label: `LEARNER_SELF_CHECKED`, not independently validated. This records commands,
changes, and results without private chain-of-thought.

## 1. Artifact inventory

Hypothesis: the examiner's blocking report reflected the files actually delivered, rather than a
solver defect hidden inside an implementation.

Experiment: listed the workspace files before editing and opened only `LEARNER_MATERIAL/`,
`PRIOR_ATTEMPT/`, `EXAMINER_FEEDBACK/`, and `JOB.md`.

Observation: the workspace had the supplied materials and three prior narrative files, but no
`src/`, `tests/`, `README.md`, `DESIGN.md`, `VALIDATION.md`, or comprehension responses.

Change: created a complete candidate artifact set in the workspace root without altering any of the
read-only source directories.

## 2. Interpreter and compilation

Hypothesis: using the unqualified interpreter would reproduce the prior environment mismatch.

Experiment: ran `/usr/bin/python3 --version` and the provided 3.11 binary with `--version`, then
compiled all six package modules using `python3 -m py_compile` under the latter.

Observation: the versions were 3.6.8 and 3.11.5 respectively; compilation under 3.11.5 exited 0
without diagnostics. I did not weaken the implementation to support 3.6 because this unit requires
Python 3.11.

## 3. Deterministic tests

Hypothesis: separating validation, projection, solver state, and CLI I/O would make contract edges
directly testable.

Experiment: ran
`PYTHONPATH=src /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s tests -v`.

Observation: the first complete run executed 28 named tests, exited 0, and ended `OK`. A later
evidence run had the same outcome in 1.254 seconds; its exact stderr transcript is preserved. Tests
cover structural/numeric/range/ID precedence, `NaN` and `1e309`, signed zero, projection clipping,
the final allowed update, numerical overflow, internal-error redaction, process streams, byte
determinism, permutation, weight scaling, and a finite grid.

## 4. Process-boundary evidence

Hypothesis: narrative statements about exit behavior were insufficient; stored bytes should be
replayable against the real entry point.

Experiment: ran the module on converged, exhausted, overflow-prone, and malformed fixtures. Stored
the nonempty streams, then ran `validation-evidence/verify_process.py`, which uses argument arrays,
captured streams, separate process groups, and a 10-second timeout.

Observation: the verifier exited 0 with `all_matches: true`. Exit codes were 0, 3, 4, and 2. Each
stdout/stderr byte count and SHA-256 matched the stored artifact, including zero-byte opposite
streams. No traceback, `NaN`, or `Infinity` leaked into an error document.

## 5. Independent learner arithmetic

Hypothesis: the sample fields could be recomputed without trusting production objective or residual
functions.

Experiment: `validation-evidence/recompute.py` parsed the captured input and output, implemented its
own threshold projection, and recomputed the objective, feasibility residual, fixed-point residual,
and raw-byte hash without importing `allocation_solver`.

Observation: it exited 0. All three numeric absolute differences were `0.0`, and the input hash
matched. This is a separate learner code path, not an independent validator.

## 6. Documentation rendering audit

Hypothesis: mathematical content was complete after the first documentation pass.

Experiment: reopened the generated Markdown as plain text.

Observation: several inline math delimiters had lost escape characters during file construction,
and one invisible separator appeared in the activation-charge paragraph. The formulas remained
interpretable but would render poorly.

Change and result: replaced inline delimiters with dollar notation, removed the invisible
character, and reread the affected sections. This was a documentation-only correction; process
outputs and solver behavior were unchanged.

## Honest endpoint

No observed learner check currently fails, and no discrepancy is concealed. A fresh
harness-controlled evaluation is still required before any independent-validation claim.
