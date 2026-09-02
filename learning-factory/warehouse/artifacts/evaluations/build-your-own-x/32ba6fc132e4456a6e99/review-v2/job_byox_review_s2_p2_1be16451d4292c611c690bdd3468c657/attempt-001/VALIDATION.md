# Independent validation record

Review date: 2026-09-02 (America/Chicago)

Candidate under review:

```text
/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_1be16451d4292c611c690bdd3468c657/attempt-001/CANDIDATE
```

`CANDIDATE/` was treated as immutable. Temporary probe sources and build
directories were created in its writable parent workspace and removed after
use. Candidate-owned scripts are identified below; their passing results are
observations, not independent proof of a validation label.

## Toolchains

Exact commands, invoked from the attempt root:

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

The configured roots were not added to `PATH`.

## Integrity, file types, and metadata

Aggregate command, run before and after all dynamic checks:

```text
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Both observations were identical:

```text
000b65b2911908c2a9971db4aa53c5723f33a3da18aee14e7baf16d938140350  -
```

No `*.class`, `*.log`, or `__pycache__` path remained in `CANDIDATE`. An
independent `find` check counted 49 regular files and 52 directories including
the `CANDIDATE` root, with no symlink or special-file output.

Raw hashes:

```text
$ sha256sum CANDIDATE/MANIFEST.yaml CANDIDATE/PROVENANCE.json
4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa  CANDIDATE/MANIFEST.yaml
7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2  CANDIDATE/PROVENANCE.json
```

An independent Python assertion parsed both JSON documents, checked the exact
manifest key set, project identity, manifest-to-provenance snapshot linkage,
and the conservative status fields. It exited `0` and printed:

```text
PASS metadata shape, identity, linkage, and conservative labels
```

The immutable source snapshot and upstream repository were not locally
available, so the referenced source hashes and no-copy assertion were not
independently recomputed.

## Submitted layout validator

Working directory: `CANDIDATE`.

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/validate_layout.py
```

Observed exit code: `0`.

```text
PASS required regular files: 23
PASS forbidden paths absent: 21
PASS generated paths are regular files/directories: 100 paths
PASS strict JSON and GENERATED+PARTIAL manifest: 4992856bf7771de8cafbeb472131a6808085ef91caab9b0a0c3bc6e391e957fa
PASS provenance linkage and strict JSON: 7f108057b84fe64c15150aa4ab2a8773c88d2479eff9897789e9827401b2ecb2
PASS credential-pattern scan: 49 files
```

This confirms what the submitted script actually checks. Its pattern scan is
not a general secret audit, and its output is not promotion evidence.

## Exact documented test commands

Working directory: `CANDIDATE`.

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Observed exit code: `1`, before compilation. Python raised:

```text
FileNotFoundError: [Errno 2] No usable temporary directory found in ['/tmp', '/var/tmp', '/usr/tmp', '<attempt>/CANDIDATE']
```

Also from `CANDIDATE`:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/run_reference_tests.py
```

Observed exit code: `1`, with the same pre-compilation
`tempfile.TemporaryDirectory` failure. These are the exact commands claimed in
the submitted validation record; no required `TMPDIR` setting is documented.

## Test behavior with explicit writable TMPDIR

To separate runner portability from Java behavior, a dedicated empty directory
under the attempt root was created, supplied as `TMPDIR`, and removed after
each run. The public executable line was:

```text
TMPDIR=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_1be16451d4292c611c690bdd3468c657/attempt-001/reviewer-tmp-public /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/environment/run_public_tests.py --java-home /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11
```

Observed: compilation exit `0`; overall exit `1`; `RESULT 1/5 passed`. Record
defensive copies passed. The four TODO-dependent log, election, replication,
and partition cases failed with `UnsupportedOperationException`, matching the
declared starter state.

The reference executable line was:

```text
TMPDIR=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_s2_p2_1be16451d4292c611c690bdd3468c657/attempt-001/reviewer-tmp-reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 CANDIDATE/sealed/run_reference_tests.py
```

Observed overall exit code: `0`.

```text
PublicTestMain:    RESULT 5/5 passed
ReferenceTestMain: RESULT 11/11 passed
```

No benchmark main was executed.

## Independent bounded corruption probe

A temporary package-local Java probe was compiled with the sealed reference by
the absolute `javac` above and run using the absolute `java` above, each under
`/usr/bin/timeout --signal=TERM 60`. Compilation exited `0`. The probe:

1. opened a fresh log with `maxSegmentBytes=10000` and `maxRecordBytes=128`;
2. appended and forced one one-byte value, producing a 41-byte segment whose
   stored frame length was 37;
3. changed only the length prefix to the still-valid configured value 38 and
   forced the edit; and
4. reopened the log, requiring `CorruptLogException` for evidence preservation.

Observed process exit code: `1` from the probe's assertion.

```text
REOPENED original_size=41 recovered_size=0 recovered_end_offset=0
Exception in thread "main" java.lang.AssertionError: plausibly enlarged length prefix was silently truncated
```

The probe source, compiled classes, and data directory were outside
`CANDIDATE` and were removed after the observation.

## Independent bounded locale probe

A second temporary Java probe, compiled and run with the same absolute tools
and 60-second bounds, set `Locale.Category.FORMAT` to Arabic, opened and closed
a new log, printed the generated filename, and reopened the same directory.
Compilation exited `0`; execution exited `1`:

```text
GENERATED_NAME=٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠.log
Exception in thread "main" edu.learningfactory.minilog.CorruptLogException: invalid segment name: ٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠٠.log
```

The probe and its scratch products were removed.

## Static coverage and boundary review

All submitted source and prose files were inspected. The executable sealed
suite does not contain every case advertised by `adversarial/README.md` and
does not exercise every mandatory R2 invalid-frame branch. Both independent
failures are absent from public and sealed tests. The Python runners use argv
arrays, captured output, and direct-process timeouts, but no process-group
creation or group termination.

Manifest/provenance identifiers and conservative labels are internally
consistent. `LICENSE_BOUNDARY.md` clearly marks the linked tutorial license as
unasserted and claims no copied content, but the upstream and catalog baseline
were intentionally not accessed. The reviewer workspace is not a learner view,
so exclusion of evaluator-only paths could not be transfer-verified.
