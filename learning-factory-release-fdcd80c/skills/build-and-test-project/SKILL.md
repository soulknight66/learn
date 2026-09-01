---
name: build-and-test-project
description: Build a generated or educational software project and capture reproducible evidence. Use for reference implementations, alternative architectures, production variants, or any artifact that must earn BUILDS or TESTED labels through actual commands.
---

# Build and test a project

1. Inspect the declared toolchain, lockfiles, README commands, and provenance before running code.
2. Work in the assigned isolated workspace; never edit the immutable source or grader checkout.
3. Run the narrow build first, then unit, integration, and adversarial tests that the manifest requires.
4. Use `scripts/capture_command.py` for each authoritative command. Do not use a shell string.
5. Record failures as evidence. Fix the candidate, add a regression test, and rerun the exact command.
6. Grant only labels supported by captured exit codes: GENERATED, BUILDS, TESTED, FUZZED, or BENCHMARKED.
7. Store compiler/interpreter versions, argv, elapsed time, stdout/stderr hashes, and source commit.

Never treat a worker statement or an unverified README as proof. If a required dependency is unavailable,
return PARTIAL or BLOCKED with the exact command and error.
