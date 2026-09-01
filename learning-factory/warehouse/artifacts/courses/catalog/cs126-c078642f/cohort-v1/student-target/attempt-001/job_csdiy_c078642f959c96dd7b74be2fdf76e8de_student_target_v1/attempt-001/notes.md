# Kickoff-unit learning notes

## Bounded scope

I completed the authored collision-risk kickoff only. I did not attempt or
claim completion of the cataloged course, official assignments, or labs.

My starting strength was the finite probability derivation. The deliberate
practice areas were API boundaries, dependency injection, reproducible
experiments, failure-safe output, provenance, and separating stochastic
evidence from deterministic validation.

## Concrete hypotheses and experiments

1. **Hypothesis:** evaluating the complement in log space will preserve a
   small collision probability that naive subtraction can lose.
   **Experiment:** compare the implementation at `M=10^12, N=2` with the
   known value `10^-12`, and compare a grid of small inputs against an
   independently expressed `Fraction` product. **Observation:** the small
   value remained positive and matched within `10^-27`; the small grid
   matched within the declared floating tolerance.

2. **Hypothesis:** constructing `random.Random(seed)` locally and accepting an
   injected generator will decouple simulation from module-global state.
   **Experiment:** snapshot global `random` state around a seeded simulation,
   repeat a same-seed simulation, and drive individual trials with scripted
   values. **Observation:** global state was unchanged, repeated aggregates
   were equal, and scripted duplicate/nonduplicate cases followed the input.

3. **Hypothesis:** Wilson intervals will remain meaningful near estimates of
   zero and one. **Experiment:** test counts `0`, `50`, and `100` out of `100`.
   **Observation:** the first implementation produced a lower endpoint of
   `3.469446951953614e-18` at count zero because of floating cancellation.
   Explicit mathematical endpoints corrected the representation.

4. **Hypothesis:** an explicit seed plus parameters is enough to repeat a run
   in this workspace, but is not enough for a portable provenance claim.
   **Experiment:** generate the same CLI record twice in tests and compare
   bytes; inventory the implementation-dependent inputs. **Observation:** the
   records were byte-identical locally. Python version, code revision, PRNG
   implementation, model identity, and interval method remain necessary
   provenance.

5. **Hypothesis:** 20,000 trials per required case are sufficient to expose
   visible sampling uncertainty without treating agreement as proof.
   **Experiment:** run all six cases with seed `1262020`, chosen once.
   **Observation:** all exact probabilities landed inside their Wilson
   intervals. The `65536/1000` case produced 10 noncollision trials, making
   the endpoint behavior and finite sampling error especially visible.

## Engineering lessons

- The environment is part of the product contract. The default interpreter
  was Python 3.6, so a test command that only worked on the available 3.11
  runtime would not have been a truthful handoff.
- Boundary values deserve explicit representations even when a general
  floating formula is mathematically correct.
- A fixed seed provides replay, not correctness. Scripted RNGs and exact
  references test stronger deterministic properties.
- Statistical agreement is observational evidence with a known miss rate;
  it should not replace deterministic model, schema, and failure-path tests.
- Atomic replacement changes the observable failure mode from partial content
  to old-or-new content, but locking and strongest power-loss durability are
  separate concerns.
