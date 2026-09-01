---
unit_id: unit_01_minicool_lexer_engineering
provenance: learner-authored record of commands and observed local outcomes
validation_label: LEARNER_ATTEMPT_UNVALIDATED
---

# Debugging log

This is an experiment log for the bounded MiniCOOL-0 unit. It records observable
actions and outcomes, not private reasoning.

## 2026-08-31 — toolchain selection

- Hypothesis: either permitted implementation language might already have a
  local compiler.
- Experiment: queried `g++ --version` and `javac -version` without downloading
  anything.
- Observation: G++ 8.5.0 is available; `javac` failed with `command not found`.
- Decision: use C++17. The failed Java probe changed the language choice but did
  not create or modify course artifacts.

## 2026-08-31 — pre-implementation risk list

- Longest-match risk: recognizing `<` before checking `<-`/`<=`, or `-` before
  line comments, would split valid constructs.
- State risk: ending recovery at an invalid escape would expose the remainder of
  a malformed string as unrelated tokens.
- Position risk: category-specific cursor updates could disagree on LF and
  ignored control whitespace.
- Termination risk: an error transition that emits without consuming could loop
  forever.
- Planned experiments: adjacency tests, malformed-string suffix tests,
  multiline position tests, one-byte recovery tests, and a generated long input.

Build/test failures and fixes are appended only after commands are actually
run.

## 2026-08-31 — clean build and first test run

- Experiment: ran `make clean`, `make all`, then `make test`.
- Observation: the warning-as-error C++17 build succeeded. All 16 named API
  tests passed, including the 20,000-identifier generated case.
- Failure: the CLI test stopped before launching the binary because
  `mktemp -d /tmp/minicool-cli-test.XXXXXX` reported that `/tmp` did not exist.
- Diagnosis: the script assumed a mutable global temporary directory even
  though this isolated workspace does not provide one. This was a harness
  portability defect, not evidence about CLI behavior.
- Fix hypothesis: prefer an explicitly supplied `TMPDIR`, otherwise create the
  unique temporary directory below the already-created repository `build/`
  scratch directory. Keep the exit trap so the per-run directory is removed.

## 2026-08-31 — repaired CLI harness

- Experiment: reran `make test` after redirecting temporary files into the
  repository build area.
- Observation: all 16 API tests passed, followed by all three CLI process tests:
  exact serialization with a lexical error, invocation failure, and input-file
  failure. Exit status was zero.
- Follow-up hardening: removed even the optional `TMPDIR` dependency so the
  test does not change behavior with mutable machine configuration. Added a
  second invalid-escape case to check that multiple focused errors are retained
  while punctuation inside the malformed string is not leaked as a token.

## 2026-08-31 — final clean verification

- Hypothesis: the harness fix and added combined-error regression remain
  reproducible from no build products.
- Experiment: ran, as three commands, `make clean`, `make all`, and `make test`.
- Observed result: G++ 8.5.0 compiled all C++17 translation units with
  `-Wall -Wextra -Wpedantic -Werror`. The API executable printed 18 `PASS`
  records and `18 API tests passed`. The process harness then printed three
  `PASS` records for serialization/status, invocation failure, and file-I/O
  failure. `make test` exited 0.
- Environmental note: the command wrapper printed user/group name lookup
  warnings before commands because its numeric IDs have no local names; no
  compiler/test diagnostic referred to those warnings.
- Lesson: clean-build evidence and incremental-test evidence answer different
  questions. The final record uses the former; the earlier failed run remains
  above instead of being erased.
