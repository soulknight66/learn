# MIT 6.046 Course Kickoff Brief

## Status and scope

The catalog identifies **MIT 6.046: Design and Analysis of Algorithms** as a demanding course for learners who already know introductory algorithms. This package prepares one bounded kickoff unit; it does not reproduce the MIT course, establish MIT's official topic order, or show completion of any part of the full course.

The kickoff is course-manager-authored. It uses the catalog's stated emphasis on designing and analyzing algorithms and its reference to Python to create a self-contained bridge from mathematical algorithm work to reliable software construction.

## Target learner

You should already be comfortable with:

- asymptotic notation and induction;
- sorting, binary search, and basic data structures;
- the idea of dynamic programming;
- Python functions, data classes, type hints, and `unittest`.

If dynamic programming is unfamiliar, pause this unit and review it through a lawfully available introductory source before beginning. That review is prerequisite work, not part of this unit.

## First unit

**Algorithm-to-Component Kickoff: Weighted Interval Scheduling** asks you to build a small Python component whose behavior is precise enough for another engineer to depend on. You will move through the same chain that production algorithm work requires:

1. turn an optimization problem into an explicit contract;
2. choose an efficient algorithm and state its invariant;
3. justify correctness, including deterministic tie behavior;
4. implement validation and avoid surprising side effects;
5. test against an independent, exhaustive oracle on bounded inputs;
6. document complexity and engineering trade-offs honestly.

The mathematical problem is established, but the focus is not merely obtaining an optimal value. Your component must return the prescribed schedule, reject malformed records consistently, preserve its inputs, and provide repeatable test evidence.

## Learning outcomes

By the end of this unit, you should be able to:

- write a contract that resolves boundary cases before implementation;
- connect a proof invariant to concrete program state;
- make an algorithm deterministic without relying on input order;
- distinguish a production algorithm from a small test oracle;
- test optimization code beyond a handful of examples;
- communicate assumptions, cost, and limitations to a future maintainer.

## Time box

Plan for about eight focused hours:

- 45 minutes to inspect and restate the contract;
- 90 minutes for the algorithm, invariant, and proof outline;
- 2 hours for implementation and input validation;
- 2 hours for deterministic tests and the exhaustive oracle;
- 75 minutes for the design note and comprehension responses;
- 30 minutes for a clean-room rerun and final review.

Stop at the boundary of the specified component. A command-line interface, web service, database, package publication, and generalized scheduling framework are explicitly out of scope.

## Materials available now

This unit requires only:

- this brief;
- `STUDY_TASK.md`;
- `COMPREHENSION.md`;
- Python 3's standard library and locally available standard-library documentation.

The catalog also names an MIT OpenCourseWare site, a recording collection, an assignments index, and *Introduction to Algorithms (CLRS)*. Their contents were not retrieved or verified while preparing this unit. They are not required, and no question depends on them. Do not delay the kickoff to obtain them or assume that this task is an official MIT assignment.

## Evidence and completion boundary

Your work consists of an implementation, its deterministic tests, a design note, and written comprehension responses, as listed in `STUDY_TASK.md`. Run the prescribed test command from a clean working directory and keep the result reproducible.

Submission is not the same as completion. An independent validator controls any completion record. Even a passing result covers only this kickoff unit and cannot be used to claim completion or broad coverage of MIT 6.046.

