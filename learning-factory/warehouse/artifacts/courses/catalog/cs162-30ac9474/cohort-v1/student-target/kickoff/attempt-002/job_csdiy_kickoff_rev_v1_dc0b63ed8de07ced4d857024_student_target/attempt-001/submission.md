# Unit 1 Revised Submission

This artifact is limited to the deterministic round-robin simulator kickoff. It makes no claim about completing CS162 or any later unit.

## Submitted contents

- C17 implementation: `main.c`, `parser.c/.h`, `queue.c/.h`, `scheduler.c/.h`, `report.c/.h`, and `task.h`.
- Build interface: `Makefile`; `make` builds, `make test` runs unattended tests, and `make clean` removes generated products.
- Deterministic black-box suite: `tests/run_tests.py`.
- Engineering documentation: `DESIGN.md` and `TESTS.md`.
- Formal prompt answers: `RESPONSES.md`.
- Reproducible command record: `EVIDENCE.txt`.
- Revision record: `notes.md` and `debugging-log.md`.

## Reproduction

From this directory:

```sh
make clean
make
make test
```

Validation labels and exact captured output are in `EVIDENCE.txt`. The clean strict-C17 build and 20-test suite are labeled `PASS`. Dynamic ASan/UBSan validation is labeled `NOT RUN`: the available compiler compiled instrumented objects but the host could not link its missing sanitizer runtimes. No generated executable is included in the final artifact.

This bounded unit is submitted for independent evaluation; acceptance is not asserted here.
