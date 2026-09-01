# Debugging log

This log contains concise hypotheses, commands, observed failures, and lessons;
it does not record private reasoning.

## 2026-08-31 — runtime discovery

- Hypothesis: the workspace provides Julia for the required standard-library
  project.
- Experiment: `julia --version`.
- Result: exit status 127; `/bin/bash: julia: command not found`.
- Lesson/action: continue with design, implementation, and deterministic tests,
  but label all runtime-dependent evidence unverified. No network or package
  installation was attempted.

## 2026-08-31 — midpoint and width edge cases

- Hypothesis: one textbook midpoint formula is sufficient for all finite
  endpoints.
- Static counterexample: for `left=-floatmax(Float64)` and
  `right=floatmax(Float64)`, `right-left` overflows although the midpoint is
  finite.
- Change: `_midpoint` now uses half-endpoint addition when numeric endpoint signs
  differ and difference-first addition for same-sign endpoints. The interval
  test similarly normalizes a crossing-zero width by endpoint scale.
- Evidence added: testset `large finite opposite-sign endpoints` requires the
  finite exact midpoint zero.

## 2026-08-31 — no-progress semantics

- Hypothesis: a larger iteration budget always permits another bisection step.
- Static counterexample: `1.0` and `nextfloat(1.0)` have no representable value
  strictly between them; the rounded midpoint is an endpoint.
- Change: detect the equality before evaluating the candidate and return
  `STAGNATION` with `:no_interior_float`.
- Evidence added: the counted stagnation test expects only the two endpoint
  calls even with `maxiter=100`.

## 2026-08-31 — invariant branch audit

- Hypothesis: testing only a final decimal could miss a swapped endpoint-update
  branch.
- Experiment designed: one iteration for roots on each side of the initial
  midpoint.
- Result at source level: both final intervals and strict opposite function
  signs are asserted; the implementation also asserts the invariant after each
  accepted update.
- Runtime result: unavailable.

## 2026-08-31 — exact test command

- Experiment: from `ReliableBisection/`, run
  `julia --project=. -e 'using Pkg; Pkg.test()'`.
- Result: exit status 127; `julia: command not found`.
- Consequence: no test is reported as passing, no Julia version can be recorded,
  and `EXPERIMENT.md` contains pre-specified rows rather than measurements.

## 2026-08-31 — limited static validation

- First attempt: parse `Project.toml` with Python's `tomllib`.
- Result: failed because the available Python lacks `tomllib`; this did not
  indicate a TOML defect.
- Fallback: an explicit Python check verified all six required project paths,
  module/function sentinel text, the module terminator, `using Test`, and 13
  `@testset` declarations.
- Result: exit status 0.
- Limit: this is a layout/token check, not Julia parsing or execution.

## Open debugging items

1. Run the exact Julia test command on Julia 1.8 or later and fix any parse,
   dispatch, or assertion failures it exposes.
2. Run the three specified scale cases, replace all `not run` cells in
   `EXPERIMENT.md`, and record the actual Julia version.
3. Re-check that measured evaluation counts and convergence iterations match
   the documented contract before calling the implementation stable.
