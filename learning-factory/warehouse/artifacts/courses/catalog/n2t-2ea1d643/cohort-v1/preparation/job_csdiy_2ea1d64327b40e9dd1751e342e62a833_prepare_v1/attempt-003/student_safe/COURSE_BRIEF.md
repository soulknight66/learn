# Coursera: Nand2Tetris — Kickoff Brief

## What this is

This is a six-hour, manager-authored kickoff inspired by the catalog's description of building logic gates from NAND. It is designed for a learner who is already comfortable with algorithms and wants more practice turning a compact specification into a reproducible, reviewable software artifact.

It is **not** an official Nand2Tetris week or project. Completing it does not complete the course, either course part, or any official assignment.

## The engineering focus

Small Boolean components have finite behavior, so they make an unusually clean setting for practicing the full engineering loop:

1. define interfaces and assumptions;
2. implement behind a strict abstraction boundary;
3. verify every input case deterministically;
4. make the build and test procedure reproducible; and
5. explain what the evidence proves—and what it does not.

Your algorithms background will help with correctness arguments. The new emphasis is operational: another engineer should be able to obtain the same result from the repository, understand the dependency structure, and audit the implementation constraint.

## Bounded outcomes

By the end of this unit, you should be able to:

- express Boolean behavior as component contracts;
- compose NOT, AND, OR, and a two-input multiplexer from one trusted NAND primitive;
- construct an exhaustive, independent test oracle for a finite domain;
- provide one documented command that reproduces verification; and
- distinguish functional evidence from evidence about implementation structure.

The unit stops there. Sequential logic, memory, CPU construction, machine language, virtual machines, compilers, operating systems, GUI work, and Tetris are outside this kickoff.

## Available material and limitations

Everything required for the kickoff is in this brief, `STUDY_TASK.md`, and `COMPREHENSION.md`. Choose a locally available programming language; no course-specific HDL or simulator is assumed.

The catalog snapshot contains links to Coursera pages and a supplementary repository, and it describes recordings, a textbook, and ten projects. Those contents were not retrieved. Individual official project specifications, recordings, textbook chapters, starter files, and validators are not available in this workspace. You are not expected to obtain them, and you should not bypass authentication or copy rights-unclear material into your submission.

## What completion means

Submit the requested implementation, deterministic tests, design documentation, run evidence, and comprehension responses. An independent examiner must evaluate those artifacts. A self-reported result or a prose claim is not completion evidence, and a passing result applies only to this kickoff unit.
