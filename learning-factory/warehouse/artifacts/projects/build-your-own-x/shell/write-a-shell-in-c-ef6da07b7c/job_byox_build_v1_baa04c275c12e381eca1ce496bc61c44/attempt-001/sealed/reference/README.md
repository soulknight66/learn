# Sealed reference implementation

This directory is evaluator-only. It contains an independently written implementation of the learner-visible contract, not material copied from the provenance link.

Build from the repository root:

```sh
make -C sealed/reference clean all
```

The result is `sealed/reference/msh-reference`. The implementation separates lexical/grammar validation (`src/parser.c`), retained child state (`src/jobs.c`), and shell/terminal orchestration (`src/shell.c`). It intentionally implements only the explicit grammar and built-ins in `REQUIREMENTS.md`.

This code is a pedagogical reference, not a production shell. Known limitations and hardening gaps are recorded in `sealed/production/PRODUCTIONIZATION.md`.
