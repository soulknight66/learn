# Unit 1 revised submission

This submission is limited to the deterministic round-robin simulator kickoff and is offered for independent evaluation without asserting acceptance.

## Contents

- Implementation: main.c, parser.c/parser.h, queue.c/queue.h, scheduler.c/scheduler.h, report.c/report.h, and task.h.
- Build interface: Makefile.
- Unattended tests: tests/run_tests.py.
- Engineering records: DESIGN.md, TESTS.md, RESPONSES.md, and EVIDENCE.txt.
- Revision records: notes.md and debugging-log.md.
- Package inventory: MANIFEST.txt.

Every path above is a real file in this directory. Generated objects and the rrsim executable are intentionally absent after make clean and are not evidence artifacts.

## Reproduction

From the submitted directory, run:

    make clean
    make
    make test

The clean strict-C17 build and the 22-test contract suite are labeled PASS in EVIDENCE.txt. The sanitizer check is labeled NOT RUN because compilation succeeded but the installed compiler could not link missing sanitizer runtime libraries. This limitation is not represented as a safety pass.

Completing or testing this bounded artifact does not establish completion of the course or any later unit.
