# USTC Compiler Principles: Kickoff Brief

Course ID: `course_23fa038d619a5b3482e8c8eadb3e2d78`  
Unit ID: `kickoff_01_lexical_contracts`  
Validation label: `LEARNER_SAFE_PREPARED_PENDING_HARNESS_VALIDATION`  
Provenance: manager-authored from the supplied CSDIY catalog snapshot at commit `adce8e13789dc16aa6d1fbe163e9541736defae4`; no external material was fetched.

## What this kickoff is

The catalog describes a broad USTC compiler course spanning lexical and syntax analysis, intermediate representation, backend generation, optimization, and register allocation. This packet starts much smaller: you will specify, build, and test one miniature lexer as a dependable software component.

This is a preparation unit, not an official USTC lab. It does not reproduce the catalog's linked course pages, recordings, textbook, assignment pages, Cminusf framework, or tests. Those resources are not present in this packet and are not required here.

## Why begin here

Algorithmic skill helps you understand scanning, but reliable compiler work also depends on contracts, diagnostics, modular boundaries, adversarial tests, reproducible builds, and honest evidence. A lexer is small enough to practice that full engineering loop without hiding design decisions inside a large framework.

By the end of the unit, you should be able to:

- express tokenization rules as observable behavior;
- implement maximal munch while preserving exact source locations;
- keep reusable scanner logic separate from command-line concerns;
- test overlaps, malformed input, and state transitions rather than only happy paths; and
- explain what your evidence establishes and what remains untested.

## Scope and timebox

Plan for about 8 hours and stop at 10 hours. The bounded scope is lexical analysis for the MiniLex language defined in `STUDY_TASK.md`.

Do not add parsing, semantic analysis, Flex/Bison integration, LLVM or LightIR, assembly generation, optimization, register allocation, Unicode identifiers, numeric conversion, or integration with an unavailable course framework. Record an attractive extension as future work instead of expanding the implementation.

The catalog lists no prerequisites, but that absence is only catalog data—not proof that the original course has none. This kickoff assumes that you can read C++17, use a build tool, and write basic automated tests. It supplies all domain rules needed for the exercise.

## Available materials

The required learner material is local:

- this brief;
- `STUDY_TASK.md`, containing the complete MiniLex contract and submission requirements; and
- `COMPREHENSION.md`, containing questions to answer after implementation.

The course website, recordings, textbook, official assignment index, lab framework, tutorials, and official tests were not retrieved or verified. Treat any catalog URL you encounter as an optional, unverified locator, never as a hidden dependency for this unit.

## What completion means

Submit the implementation, tests, design notes, reproducibility notes, test evidence, and comprehension responses described in the task. An independent validator must build, run, and review that evidence before this unit can be marked complete.

Even a successful result establishes only this kickoff unit. It does not establish completion of the USTC course, any official lab, or any later compiler topic.
