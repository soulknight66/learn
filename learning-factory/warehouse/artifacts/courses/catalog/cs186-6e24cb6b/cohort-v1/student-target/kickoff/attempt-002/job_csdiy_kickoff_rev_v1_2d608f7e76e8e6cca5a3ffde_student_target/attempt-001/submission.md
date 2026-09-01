# Bounded Kickoff Revision Submission

Unit: `managed_unit_01_relational_pipeline`  
Label: `LEARNER_GENERATED_UNVALIDATED`

## Outcome

The missing implementation package identified by the examiner now exists in this workspace. It
contains immutable typed data, explicit EOS, a shared single-use lifecycle, composable scan/filter/
project/limit operators, deterministic tests, design and run documentation, a comprehension response,
a manifest, a complete inventory, and content digests.

This is not a successful build claim. The documented fresh build attempt reached the declared
compiler argv and failed because `javac` is absent, with `COMMAND_EXIT_STATUS=127`. No class file was
produced, no test group ran, and no `SUMMARY` line exists. The label therefore remains unvalidated.

## Submitted identity

`artifact-inventory.txt` lists all 32 learner-generated submission paths: 21 production sources, one
test source, and ten top-level deliverable/provenance records. `SUBMISSION_SHA256SUMS.txt` verifies the
22 sources plus five stable contract/provenance files. During the captured run, that checksum file had
SHA-256:

```text
38732dfea0a0625bea7298b3d5e903c7c1e8da0b51cb1f38f5caf3335855ee79
```

The generated build scratch directory is not a submitted artifact. The mutable capture and three
revision narratives are inventoried but outside the checksum set, whose scope is documented here to
avoid implying a self-referential digest.

## Available evidence

- `SUBMISSION_MANIFEST.json` parses and agrees exactly with the complete inventory.
- `sha256sum -c SUBMISSION_SHA256SUMS.txt` reports all 27 entries `OK`.
- A comment/string-aware lexical scan reports balanced nested delimiters and correct public
  type-to-filename matches in all 22 Java files.
- The source imports only JDK collection/random classes; there is no service, SQL parser, database,
  or downloaded dependency.
- The fixed-seed data independently contains 102 predicate matches, enough to exercise limit 37.
- `test-output.txt` records the source-digest identity, fresh scratch directory, exact `javac` argv,
  missing-command diagnostic, and exit 127.

Static evidence does not establish Java compilation or relational correctness. It only makes the
submitted revision inspectable and reproducible, which was impossible for the prior missing package.

## Handoff

With a JDK 8+ available, run the Bash block in `RUN.md` from this root. A passing learner run must show
13 named passes, `SUMMARY passed=13 failed=0`, and exit status 0. Then repeat in a new scratch directory
and let the controlled evaluator run independent cases against the same source digest. Only that
evaluator may change the validation result. This bounded revision is not evidence of transfer success,
completion of this unit, or completion of the wider course.
