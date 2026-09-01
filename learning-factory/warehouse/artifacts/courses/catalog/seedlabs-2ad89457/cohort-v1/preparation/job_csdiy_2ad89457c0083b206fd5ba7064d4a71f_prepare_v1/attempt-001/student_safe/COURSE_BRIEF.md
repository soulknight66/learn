# SEEDLabs: Secure C Engineering Kickoff

Artifact classification: manager-authored learner material based on catalog metadata  
Validation label: PREPARED_UNVALIDATED

## What this packet is

This is a four-to-six-hour kickoff for a strong algorithms student who wants to build real software-engineering habits in security-sensitive C. You will turn a small binary-format specification into a component with an explicit contract, reviewable invariants, deterministic tests, and reproducible evidence.

This packet is not an official SEEDLabs lab, does not reproduce an official lab guide, and is not the full SEEDLabs course. Finishing it can establish completion of this kickoff unit only.

## Why this unit comes first

Algorithmic skill helps you reason about lengths, state, and edge cases. Production C adds machine-sized arithmetic, pointer validity, partial writes, compiler behavior, build reproducibility, and evidence that another engineer can inspect. A two-byte length-prefixed frame is deliberately small enough that you can focus on those engineering obligations rather than on application complexity.

By the end of the unit, you should be able to:

- state a memory-safety contract before writing code;
- connect size-arithmetic checks to concrete buffer accesses;
- make failure behavior observable and testable;
- separate test and sanitizer evidence from proof claims; and
- hand another engineer a deterministic build and concise design record.

## Current material boundary

The supplied catalog snapshot points to a course site, recordings, textbooks, lab setup material, and a buffer-overflow lab example. Those external contents were not retrieved or validated for this packet. Some additional URLs in the catalog text are malformed. They are therefore not prerequisites here, and you should not infer their content from their titles.

Everything required for this kickoff is in the learner packet plus ordinary local C11 build tools. If a requested compiler or sanitizer is unavailable, record that fact and the exact command attempted; do not invent a successful result.

## Safe working boundary

Work only on the self-authored toy encoder and synthetic test bytes on your local machine. Do not use setuid programs, third-party binaries, real credentials, network targets, or exploit payloads. The purpose is defensive component engineering and evidence, not exploitation.

## Bounded completion

Submit the artifacts named in `STUDY_TASK.md`, answer the prompts in `COMPREHENSION.md`, and stop after the stated timebox. A controlled validator—not a completion claim in your notes—decides whether this unit passes. Even a passing result leaves the broader course incomplete.

Provenance: scoped from the provided CSDIY catalog snapshot at source commit `adce8e13789dc16aa6d1fbe163e9541736defae4`; exercise design is newly manager-authored. No external retrieval was performed.
