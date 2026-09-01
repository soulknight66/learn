# Agent guide for the QuorumLog challenge

Work only in this challenge workspace. When acting as a learner, put work under `starter/` and do not
read or modify `sealed/`, factory control files, or provenance snapshots. Reference builders and
independent validators may inspect sealed material when their task explicitly authorizes it. Treat
tests as observations of the public contract, not as permission to hard-code examples.

## Workflow

1. Read `REQUIREMENTS.md`, then implement one milestone at a time.
2. Keep the package and public signatures unchanged.
3. Run `sh public_tests/run.sh` after each small change.
4. Add your own tests outside the supplied source tree if desired, but do not weaken supplied tests.
5. Record assumptions in your own notes and answer `DESIGN_QUESTIONS.md` in your own words.

## Engineering constraints

- Target Java 17 and use only the Java standard library.
- Preserve byte-array ownership: callers must not mutate stored or returned records indirectly.
- Keep behavior deterministic; do not add sleeps, wall-clock dependencies, randomness, threads,
  sockets, or external services.
- Reject invalid operations before partially changing state.
- Use integer IDs and offsets exactly as the contract specifies; do not special-case public-test
  values.
- Never add credentials, environment files, generated class files, or build output to the artifact.

The public suite is intentionally incomplete. Independent validation may exercise boundary values,
arbitrary failure/recovery sequences, defensive copies, constructor validation, and safety
invariants not enumerated in the examples.
