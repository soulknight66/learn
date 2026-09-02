# Repair-generation validation evidence

These are fresh local observations from repair generation 1 on 2026-09-02.
They are builder-owned evidence, not independent promotion evidence.
`MANIFEST.yaml` remains `GENERATED` + `PARTIAL`, `productionized` remains
false, and independent validation remains required.

## Exact toolchains

The configured binaries were invoked by absolute path and their roots were not
added to `PATH`.

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
```

Observed combined exit code: `0`.

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
javac 21.0.5
```

## Progressive starter observation

Exact command from the repository root, with neither `TMPDIR` nor
`--temp-root` supplied:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Observed exit code: `1`. The scratch directory was selected explicitly by the
runner rather than by Python's host-default temp lookup. `javac` exited `0`,
then the intentionally incomplete starter reported `RESULT 1/5 passed`.
Record defensive-copy behavior passed; the other four cases stopped at the
documented milestones in `SegmentedLog`, `ElectionState`, and
`ReplicationTracker`. This is an expected incomplete-starter observation, not
a passing-suite claim. The automatically created scratch root was removed.

## Sealed reference observation

Exact command from the repository root, again without `TMPDIR` or
`--temp-root`:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/run_reference_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Observed exit code: `0`. Compilation included the sealed reference, public
tests, sealed tests, and manual benchmark source. The benchmark was not run.
The Java mains reported:

```text
PublicTestMain:    RESULT 5/5 passed
ReferenceTestMain: RESULT 15/15 passed
```

The 15 sealed cases include one- through seven-byte partial headers, impossible
lengths, independently checkable length corruption, CRC corruption, mandatory
marker/version/flag/key-metadata rejection, final versus non-final torn-tail
handling, record-offset and segment-base gaps, ASCII naming under an Arabic
FORMAT locale, over-leader acknowledgement rejection, lifecycle bounds,
election behavior, fixed-majority commitment, and append atomicity. Both
corruption-preservation tests compare the bytes after the failed reopen. The
runner removed its scratch root after completion.

## Harness portability and timeout cleanup

Exact command:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -B -m unittest discover -s sealed/harness_tests -v
```

Observed exit code: `0`; `Ran 2 tests` and `OK`. One test made a fixture
repository read-only and observed scratch creation in its writable parent.
The other launched a descendant that installed a SIGTERM-ignoring handler; the
inner command intentionally returned timeout code `124`, the descendant-ready
marker was observed, and no delayed orphan marker appeared after group
cleanup.

## Structure, metadata, and credential-pattern scan

Exact command:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/validate_layout.py
```

Observed exit code: `0`.

```text
PASS required regular files: 23
PASS forbidden paths absent: 21
PASS generated paths are regular files/directories: 105 paths
PASS strict JSON and GENERATED+PARTIAL manifest: 4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa
PASS provenance linkage and strict JSON: 7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2
PASS credential-pattern scan: 53 files
```

The validator traverses only canonical generated roots, rejects symlinks and
special files there, checks every required and forbidden path, compares the
manifest with the authoritative object, parses provenance as strict JSON,
checks its identity/linkage, and scans generated regular files for private-key
and common assigned-credential patterns.

Current raw metadata hashes were also observed with:

```text
sha256sum MANIFEST.yaml PROVENANCE.json
```

Observed exit code: `0`.

```text
4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa  MANIFEST.yaml
7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2  PROVENANCE.json
```

A bounded Python assertion compared the archived top-level names with the
canonical contract and the repaired workspace:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'from pathlib import Path; root=Path("."); prior={p.name for p in (root/"PRIOR_BUILD").iterdir()}; canonical={"README.md","AGENTS.md","MANIFEST.yaml","PROVENANCE.json","LICENSE_BOUNDARY.md","REQUIREMENTS.md","CONCEPTS.md","DESIGN_QUESTIONS.md","VALIDATION.md","starter","public_tests","environment","sealed","adversarial","debugging","review_exercises","benchmarks"}; current={p.name for p in root.iterdir()}; assert prior == canonical; assert prior <= current; print(f"PASS preserved prior canonical top-level entries: {len(prior)}")'
```

It exited `0` and printed `PASS preserved prior canonical top-level entries:
17`.

Final file-type and scratch-residue commands:

```text
find README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks \( -type l -o \( -not -type f -a -not -type d \) \) -print
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks \( -name '__pycache__' -o -name '*.pyc' -o -name '*.class' -o -name '*.log' -o -name '.minilog-runner-tmp' \) -print
```

Observed combined exit code: `0`; both commands produced no output.

## Explicitly not validated

- The provenance URL was not accessed and no upstream content was copied.
- No benchmark was executed; no throughput or latency result is claimed.
- No fuzzing, profiler, process-crash campaign, filesystem fault injection,
  network test, transfer verification, security audit, or deployment occurred.
- Passing builder-owned tests does not confer `BUILDS`, `TESTED`, `REVIEWED`,
  `TRANSFER_VERIFIED`, `BENCHMARKED`, or `PRODUCTIONIZED`.
