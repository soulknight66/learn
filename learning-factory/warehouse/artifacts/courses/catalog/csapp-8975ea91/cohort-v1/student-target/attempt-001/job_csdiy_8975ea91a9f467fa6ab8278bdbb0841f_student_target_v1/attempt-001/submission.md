# Kickoff Unit Submission Summary

I attempted only the bounded first unit, “A Trustworthy Byte Histogram.” The
required implementation, engineering documents, automated tests, and
comprehension responses are under `submission/`. `notes.md` records the study
outcomes and `debugging-log.md` records experiments and the unavailable UBSan
runtime.

The ordinary strict build and test suite passed locally: one C module-check
executable and 9 Python black-box test methods, including four chunk-boundary
subcases. A separate UBSan build did not link because the runtime library was
unavailable, so no sanitizer pass is claimed. Generated binaries are removed
after validation as required.

Only these learner-safe inputs were consulted:

- `COURSE_BRIEF.md`
- `STUDY_TASK.md`
- `COMPREHENSION.md`

No optional reference, external course material, published solution, other
learner work, hidden rubric, sealed material, or factory state was consulted.
The wider course remains incomplete and unassessed. This kickoff unit is ready
for independent review; local prose and self-tests are not completion evidence.

Provenance: learner-authored from the three files listed above and locally
executed tool output.

Validation label: `LEARNER_SUBMISSION_READY_FOR_INDEPENDENT_VALIDATION`.
