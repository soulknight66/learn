# Generation-time validation evidence

This file records local observations from artifact generation. It does not
promote the artifact: `MANIFEST.yaml` remains `GENERATED` + `PARTIAL`,
`productionized` remains false, and independent validation is required.

## Exact toolchains

Commands were invoked by absolute path; neither toolchain root was added to
`PATH`.

```text
$ /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)

$ /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/javac -version
javac 21.0.5

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
```

## Starter observation

Exact command:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Observed exit code: `1`. Compilation succeeded. Runtime result was `1/5
passed`; the four failures were the deliberate `TODO` milestones in
`SegmentedLog`, `ElectionState`, and `ReplicationTracker` (with partition
integration blocked by the log milestone). This is the expected progressive
starter state, not a passing test claim.

## Sealed reference observation

Exact command:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/run_reference_tests.py
```

Final observed exit code: `0`. The runner compiled reference sources, the
manual benchmark harness, public tests, and sealed tests with `javac`. It then
reported:

```text
PublicTestMain:    RESULT 5/5 passed
ReferenceTestMain: RESULT 11/11 passed
```

An earlier informative run compiled successfully but produced `3/5` public
passes because Java's default `/tmp` parent is unavailable in this sandbox.
Both runners were corrected to create a private runtime temp directory inside
their automatically removed build directory and pass it through
`-Djava.io.tmpdir=...`. The final result above was rerun after that correction.

## Metadata and packaging observation

Exact command:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/validate_layout.py
```

The check parses both metadata files as strict JSON, compares the manifest to
its authoritative object, verifies provenance linkage, checks required and
forbidden paths, rejects symlinks/special files in the generated tree, and
scans generated regular files for private-key and common credential-token
patterns. Factory control markers are outside the scan and were not inspected.

Final observed exit code: `0`.

```text
PASS required regular files: 23
PASS forbidden paths absent: 21
PASS generated paths are regular files/directories: 100 paths
PASS strict JSON and GENERATED+PARTIAL manifest: 4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa
PASS provenance linkage and strict JSON: 7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2
PASS credential-pattern scan: 49 files
```

Observed raw file SHA-256 values before the final layout check:

```text
4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa  MANIFEST.yaml
7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2  PROVENANCE.json
```

## Explicitly not validated

- The provenance URL was not accessed and no upstream content was copied.
- The benchmark harness was compiled but not run; there are no benchmark
  results or `BENCHMARKED` claim.
- No fuzzing, profiler, network partition, process crash, filesystem fault
  injection, transfer verification, security audit, or production deployment
  was performed.
- Passing generator-owned tests does not confer `BUILDS`, `TESTED`, `REVIEWED`,
  `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`; those labels remain the independent
  validator's decision.
