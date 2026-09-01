# Algorithms I & II: bounded kickoff

## What this unit is

This is a self-contained engineering kickoff inspired by the catalog description of Princeton's Algorithms I & II sequence. It is manager-authored, not an official Princeton or Coursera lesson or project. Completing it demonstrates one bounded set of skills; it does not complete either course or the approximately 60-hour catalog entry.

The unit asks you to turn a familiar algorithm into a dependable software component. You will specify and implement union-find (disjoint-set union), exercise it through a small connectivity client, test it against an independent model, and explain the engineering decisions that make the result trustworthy.

## Driving question

Can you carry an algorithm from invariant and correctness argument through API design, implementation, adversarial testing, practical use, and reproducible evidence?

## Learning goals

By the end of this unit, you should be able to:

- state the representation invariants of a forest-based disjoint-set structure;
- connect those invariants to termination and correctness;
- implement union by size with path compression behind a precise Java API;
- distinguish worst-case claims from amortized complexity claims;
- test observable behavior without coupling tests to private array layouts;
- use a simple independent oracle for deterministic randomized testing;
- identify operational boundaries, including malformed input, mutable state, concurrency, and unsupported deletion; and
- leave a build-and-test trail that another person can rerun.

## Scope and timebox

Plan for about eight hours, with a lower bound of six and a hard timebox of ten. Produce only the two required Java classes, two executable test classes, and three short evidence documents named in the study task. Build tooling, a graphical interface, concurrency support, persistence, dynamic site creation, and edge deletion are out of scope.

You are expected to be comfortable with asymptotic analysis, arrays, trees, Java classes, exceptions, and basic command-line compilation. No prior union-find library may be used.

## Material status

Everything required for this unit is in the three learner-safe files in this directory. The catalog supplied pointers to Coursera pages, recordings, the *Algorithms, 4th Edition* website and code, and a community repository. Those payloads were not retrieved or verified for this preparation. They are optional context only and must not be treated as required or as proof that a particular official unit is available.

The catalog also says that ten official projects exist, but no individual specification, starter package, test suite, or validation contract is present here. This kickoff neither reconstructs nor substitutes for any one of those projects. Do not seek restricted solutions, hidden tests, grader internals, or enrollment-only material for this work.

## Finish line

Place the requested work under `submission/`. A prose claim, a screenshot, or the existence of these preparation files is not evidence of completion. A controlled validator must independently compile the sources, run learner and examiner checks, inspect the algorithmic constraints, and assess your written reasoning. Even after this unit is validated, the course remains incomplete pending separately sourced and validated later units.
