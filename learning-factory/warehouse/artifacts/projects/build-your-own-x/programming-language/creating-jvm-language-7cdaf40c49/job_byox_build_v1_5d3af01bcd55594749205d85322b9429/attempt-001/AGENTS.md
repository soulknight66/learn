# Learner workspace rules

- Treat `REQUIREMENTS.md` as the normative contract; examples are illustrative.
- Implement the missing behavior only under `starter/`.
- Do not read, copy, or expose `sealed/` while solving the challenge.
- Do not weaken, delete, or special-case public tests.
- Keep the compiler dependency-free and deterministic.
- Invoke subprocesses only through argument arrays if you add process-based
  tooling; never interpolate source text into a shell command.
- Generated `.class` files and build directories are scratch artifacts and must
  not be committed.
- Add tests for every diagnostic or bytecode rule you change.
- A local claim of success is not evidence; the harness-controlled validator is
  authoritative.

