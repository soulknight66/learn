# Independent review

Verdict: **REVISE**. The challenge is thoughtful and its `GENERATED` + `PARTIAL` labeling is honest,
but independent executable correctness and learner-view isolation remain unproved. The candidate was
reviewed in place and not modified.

## Prioritized findings

### P1 — Executable correctness remains unvalidated

Neither `java` nor `javac` is available. With a reviewer-writable `TMPDIR`, both supplied runners
reached line 13 and exited 127 at `javac`; no Java source was compiled and no test case ran. The
reference implementation looks coherent under static review and all 19 starter signatures have a
reference counterpart, but that does not establish `BUILDS` or `TESTED`. The builder correctly says
as much in `CANDIDATE/VALIDATION.md:5-10` and keeps independent validation required.

Before acceptance, a harness-controlled JDK 17+ environment should compile with warnings-as-errors,
run the public and sealed suites, and run independently authored defensive-copy, failed-operation
atomicity, stale-first recovery, boundary, and model-based traces. Preserve raw output; the supplied
tests alone cannot award a validation label.

### P1 — Sealed isolation is organized but not transfer-verified

The reference implementation, reference tests, and exercise answer keys are correctly grouped under
paths containing `sealed`, and no solution implementation was found in learner-facing Java sources.
However, those files are readable in the submitted tree. `CANDIDATE/README.md:77` is an instruction
not to inspect them, not evidence that a student view excludes them. No export allowlist, generated
student-view inventory, or harness validation is part of the candidate.

Do not hand this tree directly to a learner. Have the control plane generate a view that excludes
every sealed path, then independently inventory that view before any `TRANSFER_VERIFIED` claim.

### P2 — The documented verifier command has an undeclared Python-version dependency

`CANDIDATE/VALIDATION.md:95-99` records `python3 sealed/validation/verify_artifact.py` as successful,
but the script uses `from __future__ import annotations`. On this host, `python3` is 3.6.8 and the
exact command exits 1 with `SyntaxError: future feature annotations is not defined`. Invoking the
same file explicitly with Python 3.11.5 exits 0 and reproduces its configured PASS results.

Declare a supported Python minimum for validator hosts (at least a version supporting that future
feature) or make the verifier compatible with the documented environment-independent command.

### P2 — The advertised milestone test groups cannot be selected

`CANDIDATE/README.md:22-23` tells learners to wait for the current public-test group to pass before
opening the next milestone. In practice, `ContractTests.main` unconditionally invokes all 10 cases,
ignores its arguments, and aborts at the first failing later case. There is no milestone selector or
separate runner. The `<details>` sections collapse prose, but do not provide executable progressive
disclosure.

Add deterministic milestone selection (or separate milestone runners) and document the commands so
a milestone can produce an unambiguous pass before later work is attempted.

### P2 — Runner prerequisites are understated

`CANDIDATE/README.md:59` and `CANDIDATE/environment/README.md:6-9` name only Java and a POSIX shell.
Both scripts also require `mktemp`, `dirname`, `rm`, and a writable `${TMPDIR:-/tmp}`; `mktemp` is not
a POSIX-shell builtin. In this sandbox `/tmp` does not exist, so each exact runner command exits 1
before checking Java. Supplying a writable `TMPDIR` reaches the separately confirmed Java blocker.

Document these utility and temporary-directory requirements, including the `TMPDIR` workaround.

### P3 — Trace-depth wording exceeds the supplied test

`CANDIDATE/sealed/reference_tests/README.md:5-7` says the suite emphasizes “long state-transition
traces,” but `ReferenceTests.transitionTrace` contains only 13 explicit transitions, including five
appends, and has no generated oracle. The artifact appropriately does not claim `FUZZED`, and its
validation record requests long independent traces. Rename this as a deterministic scenario or add
the generated, model-compared trace requested by the adversarial exercise.

### P3 — Reuse rights and external provenance remain unresolved

Manifest/provenance identifiers and the snapshot hash agree internally. The boundary is conservative:
the linked tutorial is `NOASSERTION`, copying is disclaimed, and no vendored dependency was found.
Nevertheless, “intended for personal educational use” in `CANDIDATE/LICENSE_BOUNDARY.md:8-10` is not
an explicit license grant; there is no standard license file or SPDX identifier. Also, the recorded
catalog checkout is inaccessible here, so the CC0 evidence and non-copying assertion could not be
independently compared with source material. Add explicit generated-material terms if redistribution
is intended and retain upstream comparison as a review limitation until it can be performed.

## Evidence in favor

- The observable contract is unusually clear about exclusive offsets, ownership, ISR, failure
  atomicity, recovery, and the limits of this in-process model.
- Static inspection found no definite reachable-state violation in the reference logic and no
  required starter signature missing from it.
- The independent artifact audit found 38 regular read-only files, no symlinks, no archived Java
  products, no non-standard Java imports, and no high-confidence credential signature hit.
- Production, benchmark, consensus, and Kafka-compatibility limitations are stated plainly; no
  measurements or production-readiness claims are fabricated.
- Learner prompts, debugging cases, review exercises, design questions, and answer-key segregation
  are useful, provided the delivery system actually hides sealed material.

## Disposition

Retain `GENERATED` + `PARTIAL`. Revise the reproducibility and milestone issues, validate a sealed-free
student export, and obtain independent JDK-backed execution plus model-based checks before promotion.
