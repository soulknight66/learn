# MIT18.06: Linear Algebra — kickoff brief

This package starts one bounded study unit. It does **not** represent completion of MIT 18.06, Gilbert Strang's textbook, the linked video series, or a full linear algebra course.

## The unit

**Linear Systems as a Tested Software Component** is an eight-hour bridge from mathematical algorithm knowledge to dependable implementation. You will reason about the solution set of a square system, design a small solver contract, implement Gaussian elimination with partial pivoting, and test both mathematical and software failure modes.

The unit is aimed at a student who is already comfortable with algorithms, asymptotic analysis, Python, and basic matrix notation. You do not need prior numerical-computing library experience.

By the end of the unit, you should be able to:

- connect row operations, pivots, and the classification of a system's solution set;
- turn a mathematical procedure into a precise software interface;
- implement elimination and back substitution without outsourcing the core algorithm;
- explain and test a tolerance policy and partial-pivoting policy;
- distinguish exact correctness claims from empirical residual checks; and
- document where an educational solver stops being production-ready.

## Boundaries

This first unit covers dense, finite, real-valued, nonempty square systems. It does not cover a general matrix package, least squares, eigenvalues, sparse solvers, a complete floating-point error analysis, or the broader MIT course sequence.

The kickoff was authored from a catalog snapshot. The snapshot named an MIT OpenCourseWare site, recordings, assignments, *Introduction to Linear Algebra*, a textbook landing page and cover, and the 3Blue1Brown playlist. None of that remote instructional content was fetched or verified for this package. Those items are optional discovery leads, not prerequisites. All required directions are local in this folder.

## Working method

Use [STUDY_TASK.md](STUDY_TASK.md) as the build specification and [COMPREHENSION.md](COMPREHENSION.md) as the question set. Keep a short decision log while working, especially for validation, tolerance, exceptions, mutation, and tests. Prefer small commits or checkpoints that separate contract design, implementation, tests, and documentation.

Completing this unit can establish one foundation only. Later course work must be separately scoped, sourced, and validated.
