# Independent validation record

Date: 2026-09-02 (America/Chicago)

All commands ran from the review workspace root unless a command is explicitly
shown after `cd CANDIDATE`. `CANDIDATE/` was treated as immutable and was not
edited. Repeated `/usr/bin/id: cannot find name for user/group ID` lines were
environment noise; they did not change the recorded command exit codes.

## Toolchains

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Exit 0: `Python 3.11.5`.

```text
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Exit 0: OpenJDK `21.0.5`, Temurin runtime `21.0.5+11-LTS`.

```text
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
```

Exit 0: `javac 21.0.5`.

The configured roots were not added to `PATH`.

## Inventory and immutable-boundary checks

```text
/usr/bin/find CANDIDATE -type f -print | /usr/bin/wc -l
/usr/bin/find CANDIDATE -type d -print | /usr/bin/wc -l
/usr/bin/find CANDIDATE -type l -print | /usr/bin/wc -l
```

All exited 0 and reported 53 regular files, 53 directories, and 0 symlinks.
`file --mime-type` classified every regular file as text.

```text
/usr/bin/find CANDIDATE -type l -o \( -not -type f -a -not -type d \) -print
/usr/bin/find CANDIDATE -type f \( -name '*.class' -o -name '*.pyc' -o -name '*.log' -o -name '.DS_Store' \) -print
```

Both exited 0 with no output: no symlink/special path and no generated build or
log residue was found in the candidate.

`git status` and `rg --files` could not run because `git` and `rg` were absent
from `PATH` (exit 127). Read-only `find`, `grep`, `sed`, `nl`, `file`, and JDK
fallbacks were used.

## Metadata and layout

An independent Python 3.11.5 check parsed both metadata files with a
duplicate-key-rejecting `object_pairs_hook`, asserted the exact manifest key
set, cross-checked project/source/commit/snapshot identities, and asserted
`GENERATED` + `PARTIAL`, `productionized: false`, and
`independent_validation: REQUIRED`.

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -I -B -c '<strict JSON and identity/status assertions recorded above>'
```

Exit 0:

```text
PASS strict metadata identity/status linkage
MANIFEST_SHA256=4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa
PROVENANCE_SHA256=7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2
```

The hashes were separately reproduced with:

```text
cd CANDIDATE
/usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json
```

Exit 0 with the same two values.

```text
cd CANDIDATE
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/validate_layout.py
```

Exit 0:

```text
PASS required regular files: 23
PASS forbidden paths absent: 21
PASS generated paths are regular files/directories: 105 paths
PASS strict JSON and GENERATED+PARTIAL manifest: 4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa
PASS provenance linkage and strict JSON: 7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2
PASS credential-pattern scan: 53 files
```

This is builder-supplied validator output observed by the reviewer; it was
corroborated by the independent inventory and metadata checks and is not treated
as self-proving promotion evidence.

## Compilation and supplied suites

```text
cd CANDIDATE
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Compilation exited 0; the Java run and wrapper exited 1, as expected for the
starter:

```text
PASS record defensive copies
FAIL segmented log round trip -> UnsupportedOperationException: TODO milestone 3
FAIL election term and freshness -> UnsupportedOperationException: TODO milestone 4
FAIL majority high watermark -> UnsupportedOperationException: TODO milestone 5
FAIL partition read isolation -> UnsupportedOperationException: TODO milestone 3
RESULT 1/5 passed
```

A sequential repeat produced the same result and left no
`.minilog-runner-tmp` scratch root.

```text
cd CANDIDATE
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/run_reference_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Exit 0. `javac` exited 0, then the two Java mains reported:

```text
PublicTestMain:    RESULT 5/5 passed
ReferenceTestMain: RESULT 15/15 passed
```

```text
cd CANDIDATE
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -m unittest discover -s sealed/harness_tests -v
```

Exit 0: `Ran 2 tests` and `OK`. The timeout fixture printed the intentional
`TIMEOUT after 0.75 seconds`; the suite observed no surviving orphan marker.

These are reviewer-observed executions of builder-owned suites. They corroborate
specific behavior but do not confer `BUILDS`, `TESTED`, or `REVIEWED`.

## Independent behavioral probes

The reviewer created a temporary Java source outside `CANDIDATE/` (SHA-256
`e229dd3fcdd57585f57efe1baed354238b9178072dd1127d3379ac0af86a42f5`), compiled
it with the sealed reference by invoking the configured `javac` directly, and
ran it with the configured `java` directly. Compilation and execution both
exited 0.

```text
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -encoding UTF-8 -d .review-tmp/classes <eight sealed reference sources> IndependentReviewMain.java
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -ea -Djava.io.tmpdir=<review-workspace>/.review-tmp -cp .review-tmp/classes edu.learningfactory.minilog.IndependentReviewMain
```

Observed output:

```text
PASS 6 independent behavioral checks
OBSERVED externally_desynchronized_partition_partial_mutation=true
```

The six passing checks covered:

- null and empty keys remaining distinct after reopen;
- invalid over-limit append leaving offset, bytes, and segment count unchanged;
- one over-segment-limit frame in an empty segment followed by rotation;
- a five-replica majority and strict `< highWatermark` visibility boundary;
- stale-position acknowledgement refreshing contact without regressing progress;
- repair of a three-byte final partial header.

The failing atomicity scenario was:

```java
SegmentedLog log = SegmentedLog.open(directory, 10_000, 16); // end 0
ReplicationTracker tracker = new ReplicationTracker(
        Set.of("a", "b", "c"), "a", 4, 0, 10, 100, 0);
PartitionLeader leader = new PartitionLeader(log, tracker);
tracker.advanceLeaderEndOffset(2);                          // retained alias
leader.append(4, 1, null, new byte[] {9}, true);            // throws
```

After the exception, `log.endOffset()` was 1 and
`tracker.leaderEndOffset()` was 2. Inspection ties the mutation order to
`PartitionLeader.java:37-38` and the regression rejection to
`ReplicationTracker.java:94-100`.

A minimized follow-up probe (temporary source SHA-256
`56ad8d3a308acd99483e8d5bc1a4158d2484a75ff0b81dd8a78205178f1d34d1`) closed
and reopened the affected log. Direct compilation and execution again exited 0
and printed:

```text
failure=IllegalArgumentException live_log_end=1 tracker_end=2 reopened_log_end=1
```

This confirms the divergent record survived a close/recovery cycle rather than
being only an in-memory observation.

## API and deterministic-dependency review

Starter and reference sources were compiled into separate scratch class trees.
The configured absolute `javap -public` was run for all outer public classes,
records, and enums. After ignoring the implementation-only `synchronized`
modifier, output comparison reported `source_signature_compatible=true`; the
only raw differences were `synchronized` on the six reference `SegmentedLog`
methods.

```text
/usr/bin/grep -RIn -E 'currentTimeMillis|Instant\.now|new Date|System\.nanoTime|ProcessBuilder|Runtime\.getRuntime|Socket|java\.net|java\.sql|javax\.' CANDIDATE/starter CANDIDATE/sealed/reference CANDIDATE/public_tests CANDIDATE/sealed/reference_tests
```

Exit 1 with no matches. Import inspection found Java standard-library packages
only. The intentionally manual sealed benchmark, which was not run, is outside
this scan and uses `System.nanoTime` only to measure its explicit benchmark.

Python subprocess inspection found the expected `subprocess.Popen` in
`environment/process_runner.py`; static review confirmed an argv list, captured
stdout/stderr, a 60-second default timeout, `start_new_session=True`, and
SIGTERM/SIGKILL process-group cleanup. No `shell=True` or `os.system` call was
found.

## Progressive disclosure, claims, and license boundary

Documentation, source, and tests were inspected line by line. The milestone
order and R1-R7 contract are clear, but the public suite has no direct
`RecordCodec` milestone check. Searches for `allowlist` and `learner-visible`
found prose assertions only; no machine-readable learner-view projection was in
the candidate. Consequently, student isolation and transfer remain
inconclusive.

`MANIFEST.yaml`, `README.md`, `VALIDATION.md`, benchmark notes, sealed review,
and productionization notes consistently avoid stronger labels and explicitly
state what was not run. The provenance and license files consistently separate
the CC0 catalog metadata from the linked tutorial's `NOASSERTION` license and
claim no linked-content copying. The upstream snapshot/tutorial was unavailable
and was not fetched, so those historical and authorship claims were not
independently proven.

## Cleanup and unavailable checks

The temporary reviewer Java sources and scratch class trees were removed after
observation; no candidate file was changed. Running supplied runners in
parallel once left an empty attempt-parent `.minilog-runner-tmp` due shared-root
cleanup timing; the reviewer removed that empty root, repeated the public runner
sequentially, and observed no residue. Concurrent runner safety is not claimed
by the candidate.

No benchmark, fuzzing, profiler, process-crash campaign, storage fault injection,
network/security exercise, deployment, transfer, or alternate-JDK/filesystem run
was performed. FileChannel short-operation/write-failure behavior remains based
on static inspection rather than an instrumented storage provider.
