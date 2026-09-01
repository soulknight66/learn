# Jonesforth-inspired stack machine challenge

Build a small concatenative language in x86-64 assembly. The supplied interface is deliberately
narrow: source arrives on standard input, a compiler turns tokens into private bytecode, and a
stack VM executes that bytecode. The exercise is independent work based only on the catalog topic;
no linked tutorial code or prose is included.

## Progression

1. Produce a static Linux executable and handle empty input.
2. Split bounded input into tokens and parse signed decimal literals.
3. Compile literals and built-in words without executing them yet.
4. Execute arithmetic, stack manipulation, comparison, and output words.
5. Make every failure deterministic, including overflow and malformed programs.

The observable contract is in REQUIREMENTS.md. CONCEPTS.md explains the ideas without prescribing
an implementation, and DESIGN_QUESTIONS.md supplies checkpoints for written reasoning.

## Quick start

From this repository root:

    make -C starter
    printf '2 3 + .\n' | starter/stackvm
    python3 -m unittest discover -s public_tests -v

The starter is intentionally incomplete: it builds and accepts an empty program, but reports a
compile error for non-empty input. Replace its TODO path while keeping the command-line contract.
Public tests are examples, not an exhaustive validator.

## Constraints

- Target x86-64 Linux and GNU binutils; do not use libc.
- Read only standard input. Write language output only to standard output and diagnostics only to
  standard error.
- Keep all storage bounded and reject oversized input.
- Do not inspect evaluator-only material or use the linked upstream implementation as a source.

Status is GENERATED + PARTIAL. Local observations are recorded in VALIDATION.md, but only an
independent harness may award stronger validation labels.

