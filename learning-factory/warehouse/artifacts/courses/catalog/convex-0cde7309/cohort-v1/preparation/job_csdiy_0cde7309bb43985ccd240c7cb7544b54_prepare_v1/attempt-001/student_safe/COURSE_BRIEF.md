# Course brief: bounded kickoff

> This package prepares one manager-authored kickoff unit. It is not an official Stanford assignment, does not reproduce EE364A, and cannot establish completion of the course.

## Course context

The catalog identifies **Stanford EE364A: Convex Optimization** as an advanced course using Python and drawing on calculus, linear algebra, probability, and numerical analysis. Its description emphasizes that small modeling choices can substantially change how tractable an optimization problem is.

The catalog also points to a course website, recordings, a textbook landing page, and assignments. Those external materials were not retrieved or verified for this package. They are not required for this unit.

## This unit

**Trustworthy Convex Allocation Solver** is a 6–8 hour, offline software lab. You will turn a small convex model into a deterministic Python program with explicit contracts, numerical stopping behavior, tests, and provenance. The point is not merely to produce plausible numbers; it is to make the relationship between model, algorithm, implementation, and evidence reviewable.

By the end of the unit, you should be able to:

- justify convexity and uniqueness for a quadratic objective over a simplex;
- implement projected gradient descent and simplex projection;
- define input, output, validation, and failure contracts before coding;
- use invariants and metamorphic properties alongside example-based tests;
- distinguish a learner self-check from independent validation; and
- analyze how a small model change affects the assumptions behind solver guarantees.

## Expected background

You should be comfortable with Python modules and `unittest`, vectors and norms, derivatives of quadratics, sorting-based algorithms, floating-point tolerances, and basic asymptotic reasoning. No optimization library is assumed or permitted for the core solver.

## Suggested timebox

- Model and hand trace: 45–60 minutes
- Implementation: 2.5–3 hours
- Testing and failure handling: 1.5–2 hours
- Design, validation evidence, and comprehension responses: 1–2 hours

Stop after the specified solver and evidence are complete. A general-purpose optimizer, graphical interface, web service, large benchmark suite, or production deployment is outside this unit.

## What completion means

Finishing the work creates a candidate unit submission. Learner-authored prose, a green self-test run, or the presence of files is not independent evidence. A harness-controlled validator must evaluate the submission separately. Even a validated pass applies only to this kickoff; the rest of the course remains unprepared and incomplete.

---

Document provenance: course-manager-authored from the supplied CSDIY catalog snapshot for `course_0cde7309bb43985ccd240c7cb7544b54`; no linked content was retrieved.
