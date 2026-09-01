# SJTU Compiler Principles — Kickoff Brief

Course ID: `course_94560b3a323bb4da6a3c762995a4958b`  
Unit ID: `kickoff_slp_interpreter_v1`  
Validation label: `PREPARED_UNVALIDATED`

## What this unit is

This is a self-contained first study unit on engineering a straight-line program interpreter in C++17. It uses the catalog label “Lab 1: Straight-line Program Interpreter” as a topic signal, but its specification was written for this learning-factory attempt. It is not the unavailable SJTU lab handout and does not claim to reproduce official course content.

The catalog describes a roughly 150-hour compiler course. This kickoff is deliberately limited to about 10 hours. Completing it demonstrates only the outcomes listed here; it does not complete the course or establish readiness for later lexer, parser, type-checking, escape-analysis, or LLVM work.

## Why begin here

A tiny language exposes the central shape of a compiler implementation without requiring a lexer or parser first: represent syntax, traverse trees, maintain semantic state, define errors, and test observable behavior. For a learner already comfortable with algorithms, the emphasis is on turning a correct recursive idea into maintainable software:

- explicit interfaces and invariants;
- deterministic evaluation order;
- deliberate ownership and mutation boundaries;
- testable I/O and structured failures;
- reproducible builds and focused tests; and
- concise engineering documentation.

## Outcomes

By the end of this unit, you should be able to:

1. model statements and expressions as a type-safe abstract syntax tree;
2. implement a stateful interpreter with precisely documented behavior;
3. implement a pure structural analysis over that same tree;
4. handle invalid programs and integer errors without undefined behavior;
5. build and test the project from a clean directory; and
6. justify ownership, error, complexity, and testing decisions.

## Assumed background

You should be comfortable with recursion, maps, asymptotic analysis, C++ functions and classes, and basic build tooling. Familiarity with compiler construction is not assumed. The course catalog lists basic computer systems, data structures and algorithms, and programming fundamentals as prerequisites.

## Working boundary

Everything required for the unit is specified in `STUDY_TASK.md`. Do not depend on an external textbook, course website, slide deck, or framework repository. Those resources were only linked or described in the catalog snapshot and were not retrieved or verified for this job. In particular, the catalog says the newest framework is not open-sourced; it is outside this unit.

The following are intentionally out of scope:

- source-text parsing, lexing, and grammar design;
- type checking, escape analysis, intermediate representation, and LLVM;
- compatibility with any SJTU or third-party framework;
- networking or third-party package downloads; and
- performance tuning beyond clear linear traversals.

## Suggested timebox

- 1 hour: read the specification and sketch interfaces and invariants.
- 2 hours: implement the AST and a small construction fixture.
- 3 hours: implement interpreter state, output, and errors.
- 1.5 hours: implement the structural analysis.
- 1.5 hours: add edge-case and interaction tests.
- 1 hour: clean-build, document decisions, and answer the prompts.

If you reach the timebox, preserve a compiling, tested subset and document the remaining gap. Do not silently widen the assignment into later compiler phases.

## Completion boundary

Your own checklist is useful feedback, but it is not completion evidence. This unit can be recorded as complete only after an independent worker-harness validator checks the build, behavior, tests, documentation, and comprehension submission. Even then, only this kickoff unit—not the whole course—is complete.

## Provenance

This learner brief was manager-authored from the catalog snapshot in `JOB.md`, whose source-derived content hash is `c0b01a3547deab67a2c9ce70808ae093949cc577ef4b3208bb40f409922c4189` at source commit `adce8e13789dc16aa6d1fbe163e9541736defae4`. No external resource was retrieved. `PREPARED_UNVALIDATED` means the material is ready for independent review, not that learner work has passed.
