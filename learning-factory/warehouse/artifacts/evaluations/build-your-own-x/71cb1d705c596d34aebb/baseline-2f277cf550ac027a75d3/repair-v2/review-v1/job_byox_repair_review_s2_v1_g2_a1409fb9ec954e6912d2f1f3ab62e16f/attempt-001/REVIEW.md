# Independent review

Project: `project_88e5a9a922f8f9e2166223c1333f28f9`  
Builder job: `job_byox_repair_s2_v1_g2_40e84b613b5a0b0bdb0a4207727452c3`

## Advisory verdict

**PASS.** No blocking correctness, isolation-structure, provenance-boundary, or
validation-honesty defect was found. This verdict is advisory only. It does
not publish or authorize the `REVIEWED` label; only the separate
orchestrator-captured acceptance validator may do that.

## Prioritized findings

### P0 — none

No critical finding.

### P1 — none

No correctness or learner-safety finding requiring revision.

### P2 — environment preflight is narrower than the test runtime

`environment/check.sh` verifies the compiler, interpreter, `/bin/sh`, and a
`printf` location, then reports `environment prerequisites present`. The
public and sealed suites additionally depend on utilities including `cat`,
`grep`, `tr`, `/bin/sleep`, `/bin/pwd`, and `/bin/true`, plus GNU Make and PTY
capabilities. `environment/README.md` names some, but not all, of those
fixtures, and the check does not probe most of them.

Impact is low on the configured host, where every exercised dependency was
available and all suites passed. For reproducibility elsewhere, enumerate the
complete fixture set and either probe it or make the preflight message
explicitly partial.

## Review basis

### Correctness and reproducibility

- The starter and sealed reference built warning-clean with the configured GCC
  15.2.0 in a writable copy of the immutable submission.
- Fresh normal runs passed 11 public, 17 sealed, and 6 adversarial tests.
- Fresh ASan/UBSan runs passed the same 34 tests with no reported sanitizer
  error; leak detection was explicitly disabled.
- GCC `-fanalyzer` completed without a diagnostic.
- Twenty-one reviewer-authored edge assertions passed. They covered invalid
  invocation, previous-status `exit`, invalid `exit`, `0666` creation filtered
  by umask, child-context built-ins, pipeline process-group identity,
  monotonically increasing job IDs, default `fg`, and invalid job operands.
- A separate forced timeout proved TERM/KILL escalation removed a
  SIGTERM-ignoring same-group descendant within a bounded interval.
- The starter's expected incompleteness is transparent: its default `check`
  ran all 11 public tests, passed 2, failed 9 behaviorally, and selected the
  pinned Python without an interpreter error.

### Progressive disclosure and learner usefulness

The learner-facing path is coherent: observable requirements, concepts,
design prompts, a compiling scaffold, and black-box public tests. Instructor
answers and the reference are under `sealed/`; adversarial, benchmark,
debugging, and review indexes identify themselves as harness-only and do not
expose answer content at their learner-facing top level. The concepts and
questions explain ownership and job-control hazards without supplying an
implementation.

The submitted pack necessarily contains both sides of that boundary. No
factory-produced learner view was present, so actual transfer exclusion was
not tested and must remain unlabelled.

### License and provenance

The generated-material CC0-1.0 grant is explicit and excludes the linked
resource whose license is `NOASSERTION`. The document distinguishes the
source-snapshot identifier from the byte digest of `PROVENANCE.json`. The
fresh audit and direct digest check agreed, and the manifest/project/source
identities were internally consistent.

The source object database and external tutorial were unavailable. Therefore
the upstream hashes, catalog license evidence, and assertion that no linked
content was copied remain provenance claims rather than independently
recomputed facts.

### Validation honesty

The manifest remains `GENERATED` plus `PARTIAL`, requires independent
validation, and says `productionized: false`. Builder validation clearly
identifies itself as builder-controlled, distinguishes benchmark smoke from a
benchmark claim, disclaims fuzzing and promoted labels, records disabled leak
detection, and lists non-production gaps. No unsupported `BUILDS`, `TESTED`,
`FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`
promotion was found.

## Remaining limitations

- One configured Linux/POSIX environment was exercised; Python 3.9 and other
  POSIX implementations were not.
- There was no fault injection, coverage-guided fuzzing, LeakSanitizer run,
  performance threshold, or production-readiness assessment.
- The reference's documented fatal-allocation, terminal-mode, logout/job
  lifecycle, and post-`getline` size-check gaps remain accepted educational
  scope limits.
- The first scratch-copy build was inconclusive because archive-preserved
  read-only modes prevented output creation. After changing only the scratch
  copy's modes, both builds and all reported checks completed. Candidate bytes
  remained unchanged.

Exact commands and observations are recorded in `VALIDATION.md`.
