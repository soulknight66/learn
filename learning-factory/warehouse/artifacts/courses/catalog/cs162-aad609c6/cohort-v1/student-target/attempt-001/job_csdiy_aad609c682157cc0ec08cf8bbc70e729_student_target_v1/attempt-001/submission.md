# Unit 1 Submission

This submission is scoped only to the deterministic round-robin simulator kickoff. It makes no claim about completing CS162 or any later unit.

## Contents

- Implementation: `main.c`, `parser.c/.h`, `queue.c/.h`, `scheduler.c/.h`, `report.c/.h`, and `task.h`.
- Build interface: `Makefile` with `make`, `make test`, `make sanitize-test`, and `make clean`.
- Deterministic tests: `tests/run_tests.py`.
- Engineering documentation: `DESIGN.md`, `TESTS.md`, and `EVIDENCE.txt`.
- Comprehension work: `RESPONSES.md`.
- Learner record: `notes.md` and `debugging-log.md`.

The implementation uses only the C17 standard library. Invalid commands and inputs are fully validated before normal output. The unattended suite covers explicit examples and boundaries plus deterministic differential cases.

## Reproduction

```sh
make clean
make
make test
```

See `EVIDENCE.txt` for captured statuses and output. The sanitizer target is included, but this environment could not link the required sanitizer runtimes; Valgrind and GDB were also unavailable. This is documented as a validation limitation, not a successful safety check.

The artifacts are submitted for independent Unit 1 evaluation; evaluator acceptance is intentionally not asserted here.
