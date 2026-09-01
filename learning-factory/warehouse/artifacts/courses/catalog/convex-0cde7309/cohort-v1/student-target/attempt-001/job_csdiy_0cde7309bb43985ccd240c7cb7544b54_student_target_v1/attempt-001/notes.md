# Kickoff Learning Notes

Provenance: learner-authored offline using only the three supplied learner-safe course files and the
implementation/experiments in this workspace. Validation label: `LEARNER_SELF_CHECKED`.

## Scope

I attempted only the Trustworthy Convex Allocation Solver kickoff. I did not retrieve linked course
material, build a general optimizer, or attempt later course units. The intended learning stretch
was the production contract around a familiar convex algorithm: validation precedence, numerical
failure, deterministic bytes, stream/exit semantics, bounded subprocesses, and honest evidence.

## Initial hypotheses

- Positive weights should make the diagonal quadratic strictly convex and the simplex should make
  existence easy, so the mathematical optimizer is unique.
- Projection should be the main place where array order can accidentally become an API defect.
- With step \(1/\max a_i\), multiplying all weights by one positive constant should leave every
  mathematical update unchanged because the scale cancels.
- A very uneven weight vector should remain feasible after each projection but can miss the
  fixed-point tolerance at a short iteration limit.
- Valid finite inputs can overflow binary64, so numerical failure needs a separate channel from
  invalid input.

Each became a deterministic test rather than remaining a prose assumption.

## Model trace

For the representative three-item input, \(x^0=(1/3,1/3,1/3)\) and \(L=4\). The gradient is
\((-7/15,-2/15,2/15)\), so the unprojected step is
\((0.45,11/30,0.3)\). Its components sum to \(67/60\); all are active and the threshold is
\(7/180\). The first projected iterate is therefore

\[
x^1=(37/90,59/180,47/180).
\]

As an independent algebra check for this instance, all optimal coordinates are positive. The
equality multiplier is

\[
\lambda=\frac{\sum_i d_i-B}{\sum_i1/a_i}=\frac{2}{7},
\]

giving \(x_i=d_i-\lambda/a_i=(18/35,9/35,8/35)\). The observed 40-update result agrees to the
requested tolerance and reports zero feasibility residual.

## Experiments and lessons

1. The first full-suite run used unqualified `python3`. Hypothesis: the workspace command matched
   the required Python 3.11. Observation: it was Python 3.6, and imports failed before solver tests.
   Lesson: a production runbook must verify the interpreter, not infer it from a command name.

2. Rerunning with CPython 3.11.5 produced 28 passing tests. A contract audit then identified four
   gaps in evidence: last-allowed-update convergence, zero/negative-zero budget behavior, a `1e309`
   numeric token, and stable unexpected-error mapping. After adding those checks and normalizing
   signed zero, the full suite produced 32 passing tests.

3. The forced-exhaustion input used weights `1` and `100`, tolerance `1e-12`, and one update.
   Observation: feasibility met tolerance while the fixed-point residual did not, and the CLI
   returned exit 3. Lesson: one combined “error” or objective-delta flag would discard useful
   state and could falsely imply convergence.

4. The overflow input used only finite values near `1e308`. Observation: gradient arithmetic became
   non-finite and the CLI returned the stable exit-4 document without `NaN`, `Infinity`, partial
   stdout, or traceback. Lesson: input finiteness is not a proof of numerical evaluability.

5. Permuting items and scaling every weight preserved the matched allocation in tests. These cases
   exercised relationships that isolated examples would not cover: ID alignment and cancellation
   between gradient scale and step scale.

## What remains uncertain

The implementation is not independently validated. Extreme finite values can still lose projection
accuracy without becoming non-finite, and an absolute tolerance is scale-sensitive. The grid oracle
has resolution `0.001` on one two-variable case. Those are limits of this kickoff evidence, not
claims about the larger course.

