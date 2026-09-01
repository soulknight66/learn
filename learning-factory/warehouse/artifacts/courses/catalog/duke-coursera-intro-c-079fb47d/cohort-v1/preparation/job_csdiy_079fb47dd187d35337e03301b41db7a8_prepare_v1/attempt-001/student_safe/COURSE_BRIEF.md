# Introductory C Programming — bounded kickoff

*Artifact provenance: course-manager-authored from the supplied CSDIY catalog snapshot. Validation label: `LEARNER_SAFE_KICKOFF_PREPARED_NOT_VALIDATED`.*

This workspace contains one self-contained, course-manager-authored kickoff unit inspired by themes in the CSDIY catalog entry for Duke's *Introductory C Programming Specialization*. It is not copied from, endorsed by, or a substitute for the Duke/Coursera course. No official lecture, textbook, or assignment content is included.

## Your goal

Build a small heap-backed integer vector in C and make its correctness inspectable. The data structure is deliberately familiar: the challenge is to turn algorithmic intuition into explicit contracts, careful ownership, deterministic tests, useful tool evidence, and a reviewable development history.

By the end of this unit, you should be able to:

- distinguish a local object, its heap allocation, and the pointers connecting them;
- state invariants that remain true at every public API boundary;
- handle invalid input, allocation failure, bounds, and size overflow without corrupting state;
- use compiler warnings, tests, GDB, and a memory checker as complementary evidence; and
- explain engineering choices so another developer can review or extend the component.

## Scope and expected effort

Plan for about seven focused hours:

1. Read and design: 45 minutes.
2. Implement the API and build rules: 2 hours.
3. Write tests and harden error paths: 1.5 hours.
4. Debug with GDB and a memory checker: 1.5 hours.
5. Document, review the Git history, and answer the comprehension prompts: 1.25 hours.

The source catalog lists no formal prerequisites. This kickoff is tuned for someone already comfortable with algorithms and at least one programming language. It assumes only a C11 compiler, `make`, Git, GDB, and either Valgrind or an AddressSanitizer/UndefinedBehaviorSanitizer toolchain. If a named tool is unavailable, record that fact and use the permitted substitute described in the task.

## Evidence and boundaries

Your work is assessed from the files, commands, test output, and reasoning you submit—not from a claim that it works. Keep output concise and reproducible; do not include machine secrets or unrelated files.

Completing this unit means only that this bounded kickoff has been evaluated. It does **not** mean that you completed an official Duke/Coursera assignment, a specialization course, or the specialization as a whole. Later units require separately retrieved, classified, and authorized materials.

Continue with `STUDY_TASK.md`, then answer `COMPREHENSION.md` in your submission.
