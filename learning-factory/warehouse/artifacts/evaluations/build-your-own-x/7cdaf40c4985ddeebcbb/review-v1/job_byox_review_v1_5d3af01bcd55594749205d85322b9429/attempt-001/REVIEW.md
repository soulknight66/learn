# Independent review

Verdict: **REVISE**. The pack is candidly labeled `GENERATED` + `PARTIAL`, and
that label should not be promoted. A reproducible provenance-binding defect must
be corrected, and Java correctness plus learner-view isolation still require
harness-controlled validation.

## Prioritized findings

### P1 — The declared provenance digest does not match the submitted file

`CANDIDATE/MANIFEST.yaml:5` declares
`0577e5701f5f7125eb6b8c378a0607e95cd98d1253e257593d3b7e739a69319a` as
`provenance_sha256`. SHA-256 over the exact submitted
`CANDIDATE/PROVENANCE.json` bytes is instead
`7945a3a2b470aff1edc4a632444e43ae0f44bf33b5f2511fc2f5c15e0e8e3797`.

The manifest value only matches the provenance object's own
`snapshot_sha256` field (`PROVENANCE.json:50`). That equality between two
declarations does not bind or authenticate the rest of the file. It conflicts
with the immutable-binding description in `LICENSE_BOUNDARY.md:10-11` and makes
the `immutable metadata binding check: PASS` claim in `VALIDATION.md:136-142`
too strong.

Required revision: define exactly which bytes or canonical payload the field
hashes and verify those bytes independently. If the intent is to hash the whole
submitted file, update the manifest to its actual digest. If it identifies a
different source snapshot, rename/document the field and add a separate content
digest for `PROVENANCE.json`.

### P1 — Build and behavioral correctness remain unverified

Independent 10-second attempts to run the public suite, sealed reference suite,
and benchmark all exited `127`: this host has neither `java` nor `javac`. No Java
source compiled, no class was loaded, and no test or measurement ran. Static
inspection found a coherent implementation and a 25-file delimiter/package/type
sanity scan passed, but those are not evidence of `BUILDS`, `TESTED`,
`BENCHMARKED`, verifier safety, or semantic correctness.

The candidate is honest about this gap in `README.md:56-60`, `MANIFEST.yaml`,
and `VALIDATION.md:44-83`. Before acceptance or label promotion, a controlled
JDK 17+ validator must compile with the declared flags, run both suites, and add
independent cases for malformed input, every resource boundary, branch spans,
class-file structure, runtime behavior, determinism, and defensive copies. The
submitted reference tests do not cover all boundary risks already listed in
`sealed/REVIEW.md:24-35`.

### P1 — Progressive disclosure is a convention, not demonstrated isolation

The full submission contains 24 files under sealed/reference/answer paths,
including the complete reference compiler, reference tests, design/review notes,
production notes, and exercise answers. `README.md:22-25` correctly says these
must not be exposed to learners, but neither `MANIFEST.yaml` nor another
deterministic file declares a learner projection, and no transfer-verification
record proves exclusion.

Do not distribute `CANDIDATE/` directly as a student workspace. Provide a
harness-owned allowlist/export manifest and a test that enumerates the produced
learner view and rejects every `sealed` segment, reference implementation,
answer, hidden test, and provenance-only internal path. If the factory already
performs this projection, preserve its validator evidence with the artifact.

### P1 — Submitted runners do not bound or isolate untrusted execution

The three scripts invoke `javac` and `java` directly
(`environment/run-public-tests.sh:19-21`,
`sealed/run-reference-tests.sh:19-21`, and `sealed/run-benchmark.sh:14-16`). None
sets a timeout, memory limit, process group, or durable captured-log contract.
The public runner also executes learner compiler code and loads its generated
class in the same JVM as the test harness.

The reviewer could make safe attempts only by supplying an outer `timeout 10s`.
Harness-controlled validation should execute each phase through argv-based,
bounded subprocesses in a process group, capture stdout/stderr and exit status,
and kill descendants on timeout. Loading learner-produced bytecode requires the
same sandbox boundary; the educational language restrictions do not constrain a
malicious compiler implementation.

### P2 — Generated-material reuse terms are unclear

The provenance boundary is appropriately cautious: it identifies the catalog as
CC0, marks the linked article `NOASSERTION`, and states that linked content was
not copied. However, `PROVENANCE.json:5` and `LICENSE_BOUNDARY.md:7-8` only call
the new material independently generated for personal educational use. There is
no top-level license grant, SPDX identifier, or explicit redistribution and
modification permission for the generated prose, source, and tests.

Choose and include an explicit license for generated material, or clearly state
that no license is granted. Keep that grant separate from both the CC0 catalog
metadata and the unlicensed linked resource. The upstream license/no-copy facts
also remain declarations here because their cited source snapshot was not
available in this review workspace.

### P2 — Milestones lack progressive executable feedback

The root guide tells learners to run one public command after each of five
milestones, but `starter/src/test` contains no files and the public harness has
only end-to-end facade checks. Its first check already requires lexing, parsing,
analysis, class emission, class loading, and execution. An M1 or M2 implementation
therefore receives little milestone-specific feedback, and the harness stops on
the first failed assertion.

Add learner-visible, non-answer-revealing checks or selectable test groups for
each milestone, with stable failure summaries. Retain end-to-end and independent
hidden tests as the acceptance boundary.

## Evidence that was satisfactory but not promotable

- The normative requirements, concepts, exercises, and sealed design discussion
  are coherent and useful for an advanced learner.
- The manifest does not self-award controlled validation labels and correctly
  leaves `productionized` false.
- Runner shell syntax passed; all 64 submitted entries inspected were regular
  files, with no symlinks or special files.
- A limited common-credential signature scan found no match.
- The candidate tree digest was identical before and after bounded test attempts.

These observations do not replace harness-controlled build, test, transfer,
license-provenance, or production validation.
