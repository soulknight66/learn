# CS420 Compiler Design: bounded kickoff

## Status and purpose

This is a six-hour, manager-authored kickoff for CS420, not an official KAIST lesson or homework. It prepares you to work on compiler code by treating AST traversal as a maintainable Rust component. Completing it does not complete CS420 and does not establish progress on the official assignments, recordings, textbooks, SSA work, optimization, or RISC-V generation.

The course catalog describes a practical Rust compiler framework called KECC, work on real C, AST printing, SSA-based IR, optimization, RISC-V generation, and fuzz testing. Those descriptions provide context only. The KECC repository and linked course materials were not retrieved for this unit, so this kickoff makes no claims about their APIs or exact sequence.

## Why this unit

Algorithmic strength helps you understand tree walks. Production compiler work also demands stable contracts, clear ownership, testable invariants, useful failures, reproducible evidence, and designs that survive new syntax. This unit focuses on that engineering layer.

By the end, you should be able to:

- express traversal order and completeness as observable invariants;
- keep traversal mechanics separate from rendering policy;
- test empty, nested, and sibling-heavy trees deterministically;
- explain Rust ownership and error-propagation choices;
- distinguish a locally proven component from an unverified integration claim.

## Starting assumptions

You should already be comfortable with recursive tree algorithms, Rust enums and pattern matching, borrowing, unit tests, and basic Cargo commands. If one of these is unfamiliar, record the gap before starting; do not hide it by claiming a command or result you did not obtain.

## Available material

The learner material for this unit is:

- this brief;
- STUDY_TASK.md;
- COMPREHENSION.md.

The catalog contains links to a course repository, recordings, a textbook section, and an assignment section. They are not local study material for this kickoff and are not required. Do not infer missing instructions from their link titles.

## Boundaries

Work on the miniature AST specified in the task. Do not build a C parser, reproduce KECC, begin an official homework, or implement later compiler stages. Construct test trees directly in Rust. Use the time box to finish a small component with reliable evidence rather than a broad prototype.

When your implementation and documentation are ready, retain the exact outputs of the commands you actually ran and answer the comprehension prompts in your own words. A separate validator will assess the submission; your own statement that it works is not completion evidence.
