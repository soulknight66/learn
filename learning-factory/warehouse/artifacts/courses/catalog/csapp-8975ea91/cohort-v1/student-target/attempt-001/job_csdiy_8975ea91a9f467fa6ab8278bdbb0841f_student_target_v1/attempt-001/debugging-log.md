# Debugging Log

All entries are from 2026-08-31 and concern only kickoff Unit 1.

## Contract review and implementation

Hypothesis: the highest-risk defects would be signed-byte indexing, premature
output, unchecked flush errors, and overflow tests that could never execute.
The implementation therefore used an unsigned input buffer, delayed the report
until successful input completion/close, checked every report operation, and
gave the opaque module a checked bulk-count update for limit testing.

## Initial strict test run

Experiment: ran `make test` from `submission/` with GCC's C11 warning set and
`-Werror`.

Observation: compilation succeeded. The C module check passed, and all 9 Python
black-box test methods passed. Negative tests confirmed expected failures for
argument count, unavailable/non-regular input, and a closed output pipe. No
functional defect appeared in this run.

Lesson: successful cases alone would not have established the important timing
property. Explicit assertions on exit status, both output streams, and exact
diagnostic bytes caught the whole observable contract.

## Clean-build reproducibility

Experiment: ran `make clean`, `make all`, and `make test`.

Observation: clean removed `build/` only; the fresh build was warning-clean;
the module check and all 9 black-box methods passed again with no skips.

Lesson: a pass after an incremental build is weaker evidence than recreating
objects and executables from source.

## Failed UBSan experiment

Hypothesis: GCC's undefined-behavior sanitizer might be available and could
provide an additional diagnostic run.

Experiment: after `make clean`, ran:

~~~text
make test CFLAGS='-O1 -g -fsanitize=undefined' LDFLAGS='-fsanitize=undefined'
~~~

Failure: both production source files compiled, but linking stopped with:

~~~text
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
~~~

Resolution: classified this as a missing local diagnostic runtime, not as test
success and not as evidence of a source defect. I made no code change for it,
cleaned the partial instrumented build, and restored the ordinary strict build.

## Final state

The final ordinary strict run and cleanup are recorded in
`submission/TEST_REPORT.md`. Remaining unforced cases are an owned-file close
failure and exact lengths 4096 and 8192; inputs immediately below and above both
boundaries were tested.

---

Provenance: learner-authored from the three supplied files and commands run in
this workspace.

Validation label: `LEARNER_DEBUG_LOG_AWAITING_INDEPENDENT_VALIDATION`.
