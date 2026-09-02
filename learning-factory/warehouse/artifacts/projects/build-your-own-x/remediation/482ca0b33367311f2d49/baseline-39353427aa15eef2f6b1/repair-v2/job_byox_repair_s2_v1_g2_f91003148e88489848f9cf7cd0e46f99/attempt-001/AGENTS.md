# Learner agent instructions

Work only in `starter/` unless an instructor explicitly asks you to add a learner test under
`public_tests/`. A valid student artifact does not contain `sealed/`, private tests, answers,
evaluator exercises, or validation evidence. If any of those are present, report a distribution
error instead of using them.

## Goal

Implement the public API in `starter/pydocklet/` using only the Python standard library. Preserve
method names, return types, exception classes, and command-line behavior described in
`REQUIREMENTS.md`.

## Engineering rules

- Never extract an archive member with `TarFile.extract()` or `extractall()`.
- Treat layer paths, image names, commands, environment values, and database contents as untrusted.
- Reject links and special archive members; keep every materialized path beneath its root.
- Use parameterized SQLite statements and explicit transactions. State claims use
  `BEGIN IMMEDIATE`.
- Launch subprocesses with an argv list, no shell, a timeout, a fresh process group, and captured
  output. Never add privilege or invoke namespace utilities with `sudo`.
- Do not weaken tests or replace a security check with a string-prefix path check.
- Use temporary directories in tests and leave no runtime state in the repository.

## Checkpoint commands

```bash
PYTHONPATH=starter python3 -m compileall -q starter
PYTHONPATH=starter python3 -m unittest discover -s public_tests -v
```

Public tests are incomplete. Add your own cases for traversal, links, whiteouts, quotas, concurrent
starts, timeouts, malformed JSON, and output truncation.
