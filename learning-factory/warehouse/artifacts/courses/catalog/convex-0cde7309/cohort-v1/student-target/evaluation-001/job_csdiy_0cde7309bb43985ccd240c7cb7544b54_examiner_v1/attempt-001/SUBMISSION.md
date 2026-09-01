# Kickoff Submission

Submission scope: candidate work for `unit_kickoff_trustworthy_convex_allocation_v1` only.

Provenance: learner-authored offline from the three provided learner-safe course files. No linked
course resources, outside repositories, rubrics, factory state, sealed references, or other student
work were used. Validation label: `LEARNER_SELF_CHECKED`; not independently validated.

## Delivered

- a standard-library Python 3.11 CLI with layered validation and exact status/stream/exit behavior;
- immutable model primitives, deterministic simplex projection, and bounded projected-gradient
  solver with both required residuals;
- raw-input SHA-256 and fixed course, unit, algorithm, and non-independent-validation provenance;
- 32 deterministic unit/CLI tests covering examples, validation, numerical failure, exhaustion,
  identical bytes, permutation, weight scaling, and a finite-grid oracle;
- design, self-check evidence, all ten comprehension responses, learner notes, and debugging record.

## Learner-run result

Under CPython 3.11.5, the full suite exited 0: 32 tests ran and the result was `OK`. The initially
available unqualified Python 3.6 command failed before test execution; that failure and the corrected
environment are preserved in `debugging-log.md` and `VALIDATION.md`.

## Honest status

This is a learner-generated candidate. Passing self-tests and complete files are not independent
evidence. A harness-controlled validator must still evaluate it. Even a validator pass would apply
only to this bounded kickoff and would not demonstrate completion of EE364A or any whole course.

