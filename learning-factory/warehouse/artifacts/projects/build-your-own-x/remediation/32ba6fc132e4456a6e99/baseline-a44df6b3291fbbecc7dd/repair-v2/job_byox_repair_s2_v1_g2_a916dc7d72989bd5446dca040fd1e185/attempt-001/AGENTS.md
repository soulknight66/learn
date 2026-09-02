# Working agreement for coding agents

Work only in this challenge repository. Do not fetch the provenance link or add
third-party dependencies. Use the configured JDK or another Java 21-compatible
JDK and keep all commands reproducible.

Learner work belongs in `starter/`. Treat `sealed/` as evaluator-only material:
do not reveal, copy, summarize, or import it into learner-visible files. Public
tests express only a subset of the contract; preserve behavior specified in
`REQUIREMENTS.md`, including failure cases not covered publicly.

Do not commit generated class files, logs, credentials, build caches, or local
absolute paths. Use the runners' automatically removed scratch directories or
select one with `--temp-root`. Never weaken checks merely to make a test pass.
Record assumptions and validation commands in the learner's own work log, not
in `MANIFEST.yaml` or `PROVENANCE.json`.

The learner-visible top-level contract is defined by
`environment/learner_view.json`. Distribution and runtime isolation are
acceptance-harness responsibilities; do not broaden that allowlist.
