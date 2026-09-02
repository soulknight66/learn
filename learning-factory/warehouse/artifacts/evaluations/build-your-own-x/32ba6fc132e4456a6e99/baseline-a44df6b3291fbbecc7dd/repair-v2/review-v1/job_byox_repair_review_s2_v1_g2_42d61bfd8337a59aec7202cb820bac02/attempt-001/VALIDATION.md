# Independent validation evidence

Review date: 2026-09-02 (`America/Chicago`). `CANDIDATE/` was treated as
immutable. Commands below ran from the attempt root unless a different working
directory is stated. `/usr/bin/id` warnings about unmapped numeric user/group
IDs appeared on commands and did not change the reported exit codes.

## Toolchains

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
```

All exited `0`. Observed versions:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
javac 21.0.5
```

The configured Python and Java toolchains were available. No alternate JDK
was configured or tested.

## Candidate immutability

A reviewer-defined aggregate was computed over each sorted relative file path,
a NUL separator, and the file bytes:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B -c '<sorted path-and-content SHA-256 calculation over CANDIDATE>'
```

Before and after all checks it printed exactly:

```text
candidate_files=56 aggregate_sha256=c411da65abbd82b7336993bfa6544c8f1028b816ab6ae26e45c3fa1b0e8c52e5
```

The final residue checks found no `*.class`, `*.pyc`, `*.log`,
`__pycache__`, or `.minilog-runner-tmp` below `CANDIDATE/`. Test projections,
compiled classes, and JShell preference scratch were created only outside the
candidate and explicitly removed after inspection.

## Reference compilation and suites

Working directory: `CANDIDATE/`.

```text
/usr/bin/timeout 120s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B sealed/run_reference_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 --temp-root ../.review-runner-scratch
```

Exit code: `0`. The runner showed the exact configured `javac` and `java`
argv. Results:

```text
PublicTestMain:    RESULT 6/6 passed
ReferenceTestMain: RESULT 15/15 passed
```

The sealed cases reported passes for framing states/bounds/semantic damage,
final versus non-final torn tails, CRC/length/offset evidence preservation,
segment validation and locale neutrality, bounded reads/lifecycle, election,
replication/ISR quorum, and partition ownership/atomicity.

## Reviewer-controlled repair scenario

The reference sources were also compiled directly, without the submitted
runner:

```text
/usr/bin/timeout 60s /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -encoding UTF-8 -d REVIEW_INDEPENDENT_BUILD/classes CANDIDATE/sealed/reference/src/main/java/edu/learningfactory/minilog/*.java
```

Exit code: `0`. A transient reviewer-owned Java main (SHA-256
`6b4bdee94a9dadedc3ebcc6d149a5a7cd5c1a2c594467809fe8ddc1c44865431`)
was compiled against those classes and run with assertions enabled:

```text
/usr/bin/timeout 60s /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -encoding UTF-8 -cp REVIEW_INDEPENDENT_BUILD/classes -d REVIEW_INDEPENDENT_BUILD/classes REVIEW_INDEPENDENT_BUILD/IndependentReviewMain.java
/usr/bin/timeout 60s /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -ea -cp REVIEW_INDEPENDENT_BUILD/classes IndependentReviewMain REVIEW_INDEPENDENT_BUILD/runtime
```

Both exited `0`; the observed line was:

```text
PASS independent ownership/atomicity/visibility scenario
```

The scenario independently asserted: misaligned-constructor rollback without
offset or byte changes; successful direct mutations after rollback; rejection
of retained log/tracker mutation aliases without offset or byte changes;
term-before-payload fencing; no byte changes for rejected payloads; aligned
valid append; majority committed visibility; tracker release and log closure.
The transient harness and build products were removed, so its digest and
assertion inventory are recorded here rather than represented as a reusable
submitted test.

## Starter baseline

Working directory: `CANDIDATE/`.

```text
/usr/bin/timeout 120s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11 --temp-root ../.review-runner-scratch
```

The `javac` child exited `0`; the Java test/wrapper exited `1` with:

```text
PASS record defensive copies
FAIL codec round trip and boundary -> UnsupportedOperationException: TODO milestone 2: encode a checked frame
FAIL segmented log round trip -> UnsupportedOperationException: TODO milestone 3: open and recover segments
FAIL election term and freshness -> UnsupportedOperationException: TODO milestone 4: implement voting rules
FAIL majority high watermark -> UnsupportedOperationException: TODO milestone 5: initialize replica state
FAIL partition read isolation -> UnsupportedOperationException: TODO milestone 3: open and recover segments
RESULT 1/6 passed
```

This matches the documented deliberately incomplete baseline. It is not
reported as a passing suite or as evidence for a validation label.

## Harness, layout, and boundary checks

Working directory: `CANDIDATE/`.

```text
/usr/bin/timeout 120s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B -m unittest discover -s sealed/harness_tests -v
```

Exit code: `0`; `Ran 4 tests in 2.664s`, `OK`. The deliberate subprocess
timeout printed `TIMEOUT after 0.75 seconds`, returned the asserted code `124`,
and its descendant-survival check passed.

```text
/usr/bin/timeout 60s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B sealed/validate_layout.py
/usr/bin/timeout 60s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B environment/project_learner_view.py . --check-source
```

Both exited `0`. Key observations:

```text
PASS required regular files: 23
PASS forbidden paths absent: 21
PASS generated paths are regular files/directories: 108 paths
PASS strict JSON and GENERATED+PARTIAL manifest: 4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa
PASS provenance linkage and strict JSON: 7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2
PASS learner-view policy: 9 included, 8 excluded top-level entries
PASS credential-pattern scan: 56 files
PASS learner-view source and policy: 9 included top-level entries, 8 excluded top-level entries, 23 regular files
```

A separate reviewer one-liner strictly parsed all three JSON objects, rejected
duplicate keys, compared project/source/commit/snapshot linkage, asserted only
`GENERATED` + `PARTIAL`, checked `productionized: false` and
`independent_validation: REQUIRED`, checked the disjoint sensitive-root
allowlist, inspected every node type, and applied independent private-key and
common token patterns. It exited `0`:

```text
PASS independent metadata/boundary audit: files=56 labels=['GENERATED', 'PARTIAL'] linked_license=NOASSERTION
```

This proves internal consistency only. The immutable source catalog and
upstream content were unavailable/not accessed, so provenance and license
assertions were not externally corroborated.

## Materialized learner view

The projector was exercised against the actual candidate, with a new
destination outside it:

```text
/usr/bin/timeout 60s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B environment/project_learner_view.py . /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g2_42d61bfd8337a59aec7202cb820bac02/attempt-001/REVIEW_PROJECTION
```

Exit code: `0` (`PASS created verified learner view`). Independent inventory
assertions then reported:

```text
PASS projected inventory: top_level=9 regular_files=23 aggregate_sha256=4ac3d2d7d8c82bc60a2fcd79ae07c5b553b0573330bc816e8439e649ec2c713d
```

The top level was exactly `README.md`, `AGENTS.md`, `MANIFEST.yaml`,
`REQUIREMENTS.md`, `CONCEPTS.md`, `DESIGN_QUESTIONS.md`, `starter`,
`public_tests`, and `environment`. The projected public runner compiled and
reproduced the same expected `1/6` TODO baseline. The projection was removed
afterward.

This verifies projection content and usability, not runtime isolation: the
source evaluator pack was still readable elsewhere in the shared review
workspace. No `TRANSFER_VERIFIED` conclusion is drawn.

## Inconclusive and intentionally omitted checks

- A JShell-local supplemental attempt could not load the compiled workspace
  classes (`ClassNotFoundException`); JShell's default execution provider also
  failed because loopback sockets are prohibited (`SocketException: Operation
  not permitted`). It was excluded from evidence and replaced by the direct
  `java` harness above.
- `rg` and `git` were unavailable in this workspace. File discovery and text
  inspection used `find`, `grep`, `sed`, and pinned interpreters; no Git-history
  claim is made.
- The upstream URL was not fetched, as required. Network/provenance comparison,
  benchmark execution, fuzzing, profiling, crash/fault injection, security
  audit, deployment, alternate-JDK testing, and production readiness remain
  unvalidated.
- Submitted scripts, tests, and prose were treated as inputs to inspect and
  rerun, not as self-authenticating proof of `BUILDS`, `TESTED`, `FUZZED`,
  `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.
