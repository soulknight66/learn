# CS162 Software-Engineering Kickoff

## Status and scope

This package prepares one bounded study unit associated with the catalog entry **CS162: Operating System**. It is a manager-authored prerequisite bridge, not an official UC Berkeley lecture, homework, project, or claim of course credit. Completing it establishes readiness for later systems work only; it does not complete CS162.

The catalog describes a demanding operating-systems course centered on C, x86 assembly, debugging, and substantial projects. The supplied snapshot does not contain a verified semester syllabus, lecture body, assignment specification, starter repository, or autograder. This kickoff therefore uses a self-contained specification and does not require any external course material.

## Unit 1: Deterministic Round-Robin Scheduler Simulator in C

**Target time:** 8 hours, with a firm 10-hour stop.

You will build a small command-line simulator whose behavior is completely determined by its input. The scheduling algorithm is intentionally familiar. The main work is software engineering: make ambiguous rules explicit, keep policy separate from mechanism, handle malformed data, manage C resources, test boundary behavior, and leave reproducible evidence.

By the end of the unit, you should be able to:

- express scheduler behavior as states, transitions, invariants, and tie-breaks;
- turn a prose contract into a defensive C interface;
- separate parsing, queueing, scheduling, metrics, and presentation;
- test ties, idle intervals, slice boundaries, failures, and resource cleanup; and
- explain engineering trade-offs with references to code and tests.

## Readiness check

Start this unit if you can already:

- use structs, pointers, arrays or dynamic allocation, headers, and separate compilation in C;
- compile from a Makefile and interpret compiler diagnostics;
- use a debugger for a small C program;
- reason about queues and asymptotic cost; and
- run commands and preserve their exact output.

If one item is unfamiliar, record it as a prerequisite gap before beginning. Do not silently expand this kickoff into the full course.

## Materials

Required learner material is entirely local:

- this brief;
- `STUDY_TASK.md`, which is the authoritative public contract; and
- `COMPREHENSION.md`, which contains the reflection prompts.

The catalog snapshot also mentions course sites, lecture videos, a textbook, Pintos-related resources, and assignments. Those external bodies were not retrieved or verified for this unit. They are neither required nor evidence for an answer. A URL in a catalog is a discovery lead, not proof that its content is available, official for a particular semester, or safe to reproduce.

## Completion boundary

Submit the program, its tests, design and test notes, command evidence, and comprehension responses described in the task. An independent evaluator decides whether this unit is complete. Your own completion claim, a successful example run, or completion of this kickoff cannot establish completion of any later course unit.
