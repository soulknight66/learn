# CMU 15-445: Database Systems — Software Engineering Kickoff

## What this packet is

This packet is a small, standalone introduction to database-systems engineering for a learner who already knows data structures and algorithms. You will build a fixed-capacity buffer-pool model in C++17, test it against failures, and explain the design decisions that make the component dependable.

The unit is manager-authored from a CSDIY catalog snapshot. It is **not** an official CMU lecture, homework, or project, and it is not a reproduction of BusTub Project #1. Finishing it can establish only that you completed this kickoff after validation; it cannot establish that you completed CMU 15-445 or any official assignment.

## Why this unit

A buffer pool sits at a useful boundary between algorithms and production engineering. Replacement policy is an algorithmic problem, but a working component also needs an explicit contract, ownership rules, failure behavior, invariant-preserving state changes, reproducible builds, and tests that detect more than happy-path mistakes.

By the end of the unit, you should be able to:

- translate a systems description into observable behavior and explicit invariants;
- implement residency, pinning, deterministic LRU replacement, dirty tracking, and write-back;
- use dependency injection and a controllable test double at an I/O boundary;
- test failure paths without relying on real disks or timing;
- discuss ownership, complexity, and concurrency risks in your own implementation.

## Assumed background

You should be comfortable with hash tables, linked structures or another deterministic recency representation, asymptotic analysis, and basic C++. You may need to learn or refresh CMake, `ctest`, interfaces, and error-return design as part of the exercise. No prior database course is required for this kickoff.

## Scope and timebox

Plan for about 8 hours. Six hours is a realistic minimum; stop after 10 hours and document unfinished items rather than silently expanding the task.

Included:

- one C++17 microcomponent with an injected page store;
- a deterministic replacement and pinning contract;
- dirty-page handling and storage failures;
- automated tests, design notes, and written reasoning.

Not included:

- the BusTub codebase or official starter code;
- real disk I/O, concurrency, background workers, or crash recovery;
- B+ trees, SQL, execution engines, query optimization, or the rest of the course.

## Materials you can rely on

The required materials are the three documents in `student_safe/`. They are designed to be sufficient for the exercise.

The catalog also names CMU schedule pages, a Fall 2022 video playlist, *Database System Concepts*, official assignments, and the BusTub repository. Those resources were not retrieved or verified for this packet. Some are only links and others are only descriptions. They are optional discovery leads, not prerequisites, and you should not assume that a link identifies an available or official unit. Do not bypass access controls or use private grading material.

## What to produce

Follow `STUDY_TASK.md` and answer the prompts in `COMPREHENSION.md`. Your evidence is the source, tests, build definition, engineering notes, and comprehension responses listed there. A prose claim that the code works is not a substitute for a repeatable build and passing tests.

Independent validation decides whether this kickoff unit is complete. Even a successful result closes only this bounded unit.
