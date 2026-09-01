# PKU Compiler Principles Practice — Kickoff Brief

This packet starts one bounded, manager-authored study unit inspired by the catalog description of Peking University's compiler practice course. It is not the complete course and is not presented as an official PKU unit.

## What the catalog establishes

The catalog describes a roughly 60-hour practice course in which learners build a compiler from a C-like language, SysY, toward RISC-V assembly, with Koopa IR as an intermediate representation. It expects programming fundamentals, data structures and algorithms, and basic computer-systems knowledge. It permits C, C++, or Rust.

The supplied snapshot does not contain the official tutorial, language or IR specifications, runtime, Docker environment, tests, or nine-step lesson sequence. Those details remain unavailable here. This unit therefore uses a small, fully specified local language and local IR. Neither should be called SysY or Koopa IR.

## Your first unit

In **A Testable Compiler Vertical Slice**, you will build the smallest useful end-to-end compiler process:

`source file → recognition/parsing → program representation → deterministic text emission`

The language has one `main` function returning one non-negative integer. The feature set is intentionally tiny; the engineering contract is not. You will define module boundaries, enforce whole-input validation, provide stable command-line behavior, test failures as well as successes, and leave reproducible evidence.

This is calibrated for a strong algorithms student who wants more practice turning a clean idea into maintainable software. Budget about six focused hours. Any implementation language is acceptable, although C, C++, or Rust aligns with the catalog.

## Outcomes

By the end of the unit, you should be able to:

- explain each boundary in a basic compiler pipeline;
- convert a written grammar and process contract into tested behavior;
- keep parsing decisions separate from deterministic rendering;
- design test partitions for valid inputs, boundary values, malformed syntax, and process failures;
- document assumptions and evidence so another engineer can reproduce your result.

## Completion boundary

Completion is decided from runnable artifacts, automated checks, written reasoning, and captured evidence—not from a claim that the work is done. Passing this unit means only that this kickoff was completed. It does not establish progress through the unavailable official sequence and never means that the whole course, SysY, Koopa IR, or RISC-V compilation has been completed.

Read [STUDY_TASK.md](STUDY_TASK.md) for the contract and [COMPREHENSION.md](COMPREHENSION.md) for the questions you must answer.
