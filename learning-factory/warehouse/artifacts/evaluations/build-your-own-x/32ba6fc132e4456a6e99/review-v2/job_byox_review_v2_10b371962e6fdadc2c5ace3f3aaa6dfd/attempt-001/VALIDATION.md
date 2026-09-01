# Independent validation record

Date: 2026-08-31  
Workspace: review attempt root; commands targeting the candidate were run from `CANDIDATE/` unless
shown otherwise. All execution attempts were bounded. No candidate file was edited.

## Outcome

The result is **REVISE**. Structural and static checks produced useful evidence, but this host cannot
compile or run Java. Consequently this review does not establish `BUILDS`, `TESTED`, `FUZZED`,
`BENCHMARKED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

## Toolchain discovery

Commands:

```sh
command -v python3 sh java javac timeout sha256sum git
python3 --version
java -version
javac -version
find /usr/lib/jvm /opt -maxdepth 4 -type f -name javac -perm -111 -print
```

Observed:

```text
python3=/usr/bin/python3
sh=/usr/bin/sh
timeout=/usr/bin/timeout
sha256sum=/usr/bin/sha256sum
Python 3.6.8
java: command not found (exit 127)
javac: command not found (exit 127)
Java candidate search: no output
git: unavailable
```

Alternate JVM/build commands `ecj`, `jshell`, `jbang`, `mvn`, `gradle`, `ant`, `groovy`, `kotlin`,
and `kotlinc` were also absent. Python modules `javalang`, `tree_sitter`, and `tree_sitter_java` were
not installed.

## Candidate immutability and inventory

Commands from the review root:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
find CANDIDATE -type f | wc -l
find CANDIDATE -type f ! -perm 0444 -print
find CANDIDATE -type l -print
```

Observed before writing reviewer outputs:

```text
9d6c0ebb08eed2a36b5f9143cbe8678edfaf25847086d4b1d35ebf77114655d9  -
38
(no non-0444 files)
(no symbolic links)
```

The same aggregate digest and empty exception lists were observed after reviewer outputs were
created. The digest covers sorted per-file paths and SHA-256 values; reviewer files are outside
`CANDIDATE/`.

## Shell parsing and runner attempts

Commands:

```sh
timeout 10s sh -n public_tests/run.sh
timeout 10s sh -n sealed/reference_tests/run.sh
```

Both exited 0 with no output.

The documented commands were then attempted exactly:

```sh
timeout 30s sh public_tests/run.sh
timeout 30s sh sealed/reference_tests/run.sh
```

Observed:

```text
mktemp: failed to create directory via template '/tmp/kafkalite-public-tests.XXXXXX': No such file or directory
public exit: 1
mktemp: failed to create directory via template '/tmp/kafkalite-reference-tests.XXXXXX': No such file or directory
sealed exit: 1
```

`/tmp` is absent in this sandbox. To separate that environmental issue from Java discovery, the
runners were retried with a writable reviewer location:

```sh
TMPDIR="$(pwd)/.." timeout 30s sh public_tests/run.sh
TMPDIR="$(pwd)/.." timeout 30s sh sealed/reference_tests/run.sh
find .. -maxdepth 1 -type d \
  \( -name 'kafkalite-public-tests.*' -o -name 'kafkalite-reference-tests.*' \) -print
```

Observed:

```text
public_tests/run.sh: line 13: javac: command not found
public exit: 127
sealed/reference_tests/run.sh: line 13: javac: command not found
sealed exit: 127
leftover scratch directories: none
```

No Java compilation or test execution occurred.

## Structural verifier

The candidate's documented command was run first:

```sh
timeout 30s python3 sealed/validation/verify_artifact.py
```

Observed exit 1:

```text
File "sealed/validation/verify_artifact.py", line 4
  from __future__ import annotations
  ^
SyntaxError: future feature annotations is not defined
```

An allowed Python 3.11.5 interpreter was then selected explicitly:

```sh
timeout 30s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3.11 \
  sealed/validation/verify_artifact.py
```

Observed exit 0:

```text
PASS required regular files: 23
PASS forbidden generated artifact paths: 0
PASS artifact entry types: regular files/directories only
PASS strict manifest/provenance object fingerprints
PASS status and labels: GENERATED + PARTIAL
PASS high-confidence credential scan: 0 hits
PASS archived Java build products: 0
PASS Java lexical structure: 8 source files
```

This independently reproduces the configured verifier outcome under Python 3.11, but a
candidate-supplied structural script is not build or behavioral evidence.

## Independent read-only artifact audit

An independent Python 3.11 audit strictly decoded both JSON objects (rejecting duplicate keys and
non-finite constants), traversed entries with `lstat`, inspected Java imports, scanned selected
high-confidence credential patterns, and cross-checked manifest/provenance identifiers. It also
counted learner-visible Java sources and public-test dispatch.

Observed:

```text
regular_files=38
irregular_entries=0
archived_java_products=0
high_confidence_credential_hits=0
java_sources=8 learner_visible_java=4
non_standard_java_imports=0
manifest_labels=['GENERATED', 'PARTIAL']
project_id_match=True
source_id_match=True
source_commit_match=True
provenance_snapshot_match=True
learner_visible_java_paths=public_tests/src/io/learningfactory/kafkalite/ContractTests.java,starter/src/main/java/io/learningfactory/kafkalite/LogRecord.java,starter/src/main/java/io/learningfactory/kafkalite/PartitionLog.java,starter/src/main/java/io/learningfactory/kafkalite/ReplicatedPartition.java
starter_unsupported_throw_count=19
public_runner_cases=10
public_runner_argument_dispatch=False
```

Credential pattern scanning is necessarily limited and is not a general secret-discovery proof.

## Static API and correctness review

A read-only regex comparison removed comments, extracted public constructor/method names and parameter
types from the three starter/reference class pairs, and compared the starter set with the reference:

```text
LogRecord.java: starter_signatures=3 reference_signatures=6 missing_in_reference=0
PartitionLog.java: starter_signatures=5 reference_signatures=5 missing_in_reference=0
ReplicatedPartition.java: starter_signatures=11 reference_signatures=11 missing_in_reference=0
total_missing_required_signatures=0
```

Manual inspection traced input validation, byte-array copying, half-open reads, append preflight,
watermark advancement, ISR removal, deterministic election, all-down recovery, and stale-first
recovery. No definite contract violation was identified in states reachable through the public API.
This is static review only. In particular, source syntax/type correctness, warnings-as-errors,
runtime exceptions, test assertions, long generated traces, and concurrency behavior remain
unverified.

The public main method always schedules 10 cases and provides no milestone dispatch. The sealed
`transitionTrace` is 13 explicit state transitions (five appends), not a long generated/model-based
trace.

## License, provenance, and disclosure checks

The recorded catalog path was checked without reading outside the allowed workspace:

```sh
test -r /projects/se/pj34000401_refsys/users/yuali01/learn/build-your-own-x/README.md
```

Observed: not readable. Network retrieval was not attempted because network access is restricted.
The CC0 catalog evidence, linked-resource content, and non-copying claim are therefore inconclusive.

No `LICENSE`, `COPYING`, `NOTICE`, or SPDX-identifier-bearing file was found. The custom
`LICENSE_BOUNDARY.md` clearly marks linked-resource licensing as `NOASSERTION`, but “intended for
personal educational use” does not define redistribution rights for generated material.

All implementation and answer material found outside the starter skeleton is under a path containing
`sealed`. That is sound organization, but there is no student-view export artifact or harness result;
because the sealed files are readable in this full submitted tree, actual disclosure isolation is
not independently established.

## Unperformed or inconclusive checks

- Java compilation and all Java test cases.
- Independently authored state-machine, property, fuzz, concurrency, or fault-injection tests.
- Benchmarks, profiling, load/soak testing, or production validation.
- A transfer test against an actual learner-view file inventory.
- External source/license comparison and plagiarism/non-copying analysis.

These limitations are reflected in `EVALUATION.json`; no candidate manifest or validation label was
changed.
