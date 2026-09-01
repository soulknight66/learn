# Bounded Kickoff Submission

Unit: `managed_unit_01_relational_pipeline`  
Label: `LEARNER_GENERATED_UNVALIDATED`

## Outcome

I produced an implementation draft of the manager-authored relational-pipeline kickoff and its
deterministic test harness. The clean build/test command was attempted, but this workspace has no
`javac` or `java`; the final attempt stopped at compilation with exit status 127. Therefore I do not
claim that the Java sources compile, that the tests pass, that an evaluator accepted the unit, or that
any larger CS186 course work is complete.

## Submitted work

- Production Java sources under `src/main/java/edu/learningfactory/relational/`
- Dependency-free test main under `src/test/java/edu/learningfactory/relational/`
- `DESIGN.md`, including boundaries, lifecycle, ownership, validation timing, errors, complexity, and
  a disk-scan extension seam
- `RUN.md`, with the exact clean build/test/capture command and JDK assumption
- `COMPREHENSION_RESPONSE.md`
- `SUBMISSION_MANIFEST.json`, labeled unvalidated
- `test-output.txt`, containing the actual failed local build attempt
- `notes.md`, `submission.md`, and `debugging-log.md`

The draft implements immutable schemas and rows, explicit EOS, observable single-use lifecycle,
exactly-once child-close propagation, scan/filter/project/limit composition, eager typed validation,
and deterministic error categories. The test main defines 13 named test groups, including fixed-seed
comparison with a separate list-based oracle.

## Evidence available

- `SUBMISSION_MANIFEST.json` parses as JSON.
- A comment/string-aware delimiter scan found balanced nested delimiters in all 19 Java files.
- Manual and independent static reviews found no remaining Java syntax/type mismatch; those reviews
  are not substitutes for `javac`.
- Two integration contradictions found during review were corrected: missing-column lookup uses its
  documented `-1` result, and close-before-open is tested as an exception.
- Additional observable checks cover zero-limit upstream pulls, text equality, projected types,
  stable composed EOS, immutable projection metadata, and failed-open rollback.
- An independent emulation of Java's fixed-seed generator found 103 qualifying records, so the
  generated test's assertion that it can reach limit 37 is not vacuous.
- The exact clean command produced `javac: command not found` and `COMMAND_EXIT_STATUS=127`; there is no
  test `SUMMARY` in the capture.

## Handoff

Install or select JDK 8+ so `javac` and `java` are on `PATH`, then run `RUN.md` unchanged from the
workspace root. Treat compiler errors or test failures as new evidence, update `debugging-log.md`, and
keep the submission label unvalidated until the worker-controlled evaluator records a result.
