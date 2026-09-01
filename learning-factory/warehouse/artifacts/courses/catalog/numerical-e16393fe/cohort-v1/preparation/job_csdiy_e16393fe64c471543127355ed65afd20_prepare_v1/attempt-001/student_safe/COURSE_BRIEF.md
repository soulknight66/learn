# Numerical Analysis Engineering Kickoff

This packet starts one bounded study unit inspired by the catalog description of MIT 18.330. It is not an MIT unit, a substitute for the course, or evidence that you have completed any part of the official course. The manager-authored work here is self-contained; the catalog's external links were not retrieved and are not required.

## Why this unit

Mathematical algorithms operate on exact objects. Software operates on finite representations, finite time, and explicit interfaces. Bisection is simple enough to reason about line by line, yet a serious implementation must still address invalid inputs, non-finite function values, scale-sensitive stopping, exhausted iteration budgets, and cases where no representable number lies strictly inside an interval.

You will turn that gap into engineering evidence: a small Julia component whose contract, internal invariant, outcomes, tests, and limitations agree.

## Bounded scope

Plan for about 10 hours:

1. Review the supplied concept notes and write the intended contract (1.5 hours).
2. Design result states and test cases before implementation (1.5 hours).
3. Implement the Julia component (3 hours).
4. Build and run deterministic tests, including extreme cases (2 hours).
5. Record a short experiment and design note (1 hour).
6. Answer the comprehension prompts from your own evidence (1 hour).

The unit covers binary floating-point behavior at an operational level, the bisection bracket invariant, mixed absolute/relative stopping, representational stagnation, API outcomes, and tests. It does not cover the full floating-point standard, general root-finding, conditioning theory, linear algebra, numerical calculus, differential equations, or the catalog's ten problem sets.

## Working concepts

- A floating-point result is a representable approximation produced under a rounding rule; familiar algebraic rearrangements need not behave identically in a program.
- Absolute error measures a difference in units. Relative error compares a difference with a chosen scale. Near zero, a purely relative requirement can lose practical meaning, so numerical interfaces often state both.
- A root bracket is an interval whose endpoint evidence supports the presence of a root under stated assumptions. An implementation should say exactly what evidence it accepts and maintain it after every update.
- A small interval is not the same observation as a small function residual. Either may be useful, but they answer different questions.
- Eventually an interval may contain no floating-point value strictly between its endpoints. More iterations cannot create a new representable value; this is an outcome the API must handle.
- A numerical routine is also a software component. Inputs, side effects, evaluation count, return states, and failures belong in its contract alongside the mathematics.

## Prerequisites and tools

You should be comfortable with continuity, roots, loop invariants, asymptotic reasoning, and ordinary unit tests. Use Julia with only its standard library. Record the Julia version you actually use. The task requires no network access and no external package.

Keep claims proportional to evidence. Passing selected tests supports those tested behaviors; it does not prove the implementation correct for every function or floating-point value, and finishing this unit does not complete the course.
