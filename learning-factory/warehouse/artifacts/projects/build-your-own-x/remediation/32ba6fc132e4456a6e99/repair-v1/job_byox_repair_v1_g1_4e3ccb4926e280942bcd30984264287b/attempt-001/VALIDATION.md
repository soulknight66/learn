# Repair validation record

Date: 2026-08-31  
Repair generation: 1  
Working directory: challenge-pack root

## Outcome and label boundary

The repaired pack remains **GENERATED + PARTIAL** and requires fresh independent validation. The
host-supported structural checks passed with the host's default Python 3.6.8. The Java runners now
reach `javac` without depending on `/tmp`, but this host has neither `javac` nor `java`; no Java
source was compiled and no public, reference, or model-based test case ran.

No learner workspace was created. The production pack now contains an exact 15-file export allowlist
and a fail-closed validator for a control-plane-created view. The allowlist passed structural checks,
and the validator rejected an intentionally incomplete existing directory. There was no positive
harness-created learner export to validate, so this is not `TRANSFER_VERIFIED` evidence.

These results do not establish `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED`. Archived prior-build or prior-review results were not
treated as current validation evidence.

The command launcher emitted the following host identity warnings before each captured invocation;
they are unrelated to pack checks:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

## Toolchain discovery

Command:

```sh
for repair_tool in python3 sh timeout sha256sum mktemp dirname rm java javac; do
    if repair_path=$(command -v "$repair_tool" 2>/dev/null); then
        printf '%s=%s\n' "$repair_tool" "$repair_path"
    else
        printf '%s=UNAVAILABLE\n' "$repair_tool"
    fi
done
python3 --version 2>&1
if [ -d /tmp ]; then printf '/tmp=present\n'; else printf '/tmp=absent\n'; fi
```

Observed exit 0:

```text
python3=/usr/bin/python3
sh=/usr/bin/sh
timeout=/usr/bin/timeout
sha256sum=/usr/bin/sha256sum
mktemp=/usr/bin/mktemp
dirname=/usr/bin/dirname
rm=/usr/bin/rm
java=UNAVAILABLE
javac=UNAVAILABLE
Python 3.6.8
/tmp=absent
```

## Script parsing

Commands:

```sh
timeout 10s sh -n public_tests/run.sh
timeout 10s sh -n sealed/reference_tests/run.sh
python3 -c 'from pathlib import Path; paths=[Path("sealed/validation/verify_artifact.py"),Path("sealed/validation/verify_student_view.py")]; [compile(path.read_text(encoding="utf-8"), str(path), "exec") for path in paths]; print("PASS Python syntax: 2 files")'
printf 'syntax_exit=%s\n' "$?"
```

Observed: both `sh -n` commands produced no output; the combined invocation exited 0 and printed:

```text
PASS Python syntax: 2 files
syntax_exit=0
```

The Python command uses `compile` without importing the scripts or writing `.pyc` products.

## Structural, provenance, status, credential, and isolation checks

Command:

```sh
timeout 30s python3 sealed/validation/verify_artifact.py
printf 'artifact_verifier_exit=%s\n' "$?"
```

Observed exit 0 under Python 3.6.8:

```text
PASS required regular files: 23
PASS forbidden generated artifact paths: 0
PASS artifact entry types: regular files/directories only
PASS strict manifest/provenance object fingerprints
PASS status and labels: GENERATED + PARTIAL
PASS high-confidence credential scan: 0 hits
PASS archived Java build products: 0
PASS learner-view exact allowlist: 15 regular files, 0 sealed paths
PASS Java lexical structure: 8 source files
artifact_verifier_exit=0
```

The verifier excludes factory control entries and the immutable `PRIOR_BUILD/` and `PRIOR_REVIEW/`
staging roots from the generated-artifact walk. Its credential scan covers generated regular files
and selected high-confidence private-key, access-token, and assigned-secret patterns; it is not a
general secret-discovery proof. Its Java check balances delimiters and checks public class/file names;
it is not compilation.

## Java runner attempts

Commands:

```sh
set +e
unset TMPDIR
timeout 30s sh public_tests/run.sh milestone-1
public_runner_status=$?
printf 'public_runner_exit=%s\n' "$public_runner_status"
timeout 30s sh sealed/reference_tests/run.sh
sealed_runner_status=$?
printf 'sealed_runner_exit=%s\n' "$sealed_runner_status"
find . -maxdepth 1 -type d \
    \( -name 'kafkalite-public-tests.*' -o -name 'kafkalite-reference-tests.*' \) -print
```

Observed:

```text
public_tests/run.sh: line 30: javac: command not found
public_runner_exit=127
sealed/reference_tests/run.sh: line 30: javac: command not found
sealed_runner_exit=127
```

The final `find` produced no output: both runner traps removed their repository-root scratch
directories. Because `/tmp` was absent and `TMPDIR` was unset, this confirms that both runners used
their documented writable-repository fallback and progressed to the separate JDK blocker. It does
not provide Java build or behavioral evidence.

The public source now dispatches `milestone-1` through `milestone-4` as independent groups of 4, 2,
3, and 1 cases; no dispatch could be executed without a JDK. The sealed suite contains a separate
fixed-seed state model for 1,024 generated operations, but that source likewise was not compiled or
run.

## Temporary-directory failure behavior

Command:

```sh
set +e
TMPDIR=environment/not-created timeout 10s sh public_tests/run.sh milestone-1
invalid_tmpdir_status=$?
printf 'invalid_tmpdir_exit=%s\n' "$invalid_tmpdir_status"
```

Observed expected exit 1:

```text
TMPDIR is not an existing writable directory: environment/not-created
invalid_tmpdir_exit=1
```

The runner did not create the named directory and failed before invoking the Java toolchain.

## Learner-view validator negative check

No student view was created. To exercise fail-closed inventory handling against an existing
non-view directory, the validator was pointed at `environment/`:

```sh
set +e
timeout 30s python3 sealed/validation/verify_student_view.py environment
incomplete_view_status=$?
printf 'incomplete_view_exit=%s\n' "$incomplete_view_status"
```

Observed expected exit 1:

```text
FAIL learner-view file inventory mismatch: missing=AGENTS.md,CONCEPTS.md,DESIGN_QUESTIONS.md,MANIFEST.yaml,REQUIREMENTS.md,environment/README.md,environment/student-view-files.txt,public_tests/README.md,public_tests/run.sh,public_tests/src/io/learningfactory/kafkalite/ContractTests.java,starter/README.md,starter/src/main/java/io/learningfactory/kafkalite/LogRecord.java,starter/src/main/java/io/learningfactory/kafkalite/PartitionLog.java,starter/src/main/java/io/learningfactory/kafkalite/ReplicatedPartition.java; extra=student-view-files.txt
incomplete_view_exit=1
```

A delivery harness must copy exactly `environment/student-view-files.txt` into an external view and
run `python3 sealed/validation/verify_student_view.py VIEW_DIRECTORY` from the production pack. A
fresh independent inventory is mandatory before any transfer claim.

## Staged-root immutability check

The prior build's paths were normalized back to the `CANDIDATE/` prefix used by the archived review
before recomputing that review's sorted per-file SHA-256 aggregate:

```sh
find PRIOR_BUILD -type f -print0 | sort -z | xargs -0 sha256sum \
    | sed 's#  PRIOR_BUILD/#  CANDIDATE/#' | sha256sum
find PRIOR_BUILD -type f | wc -l
find PRIOR_BUILD -type l -print
find PRIOR_REVIEW -type l -print
```

Observed exit 0:

```text
9d6c0ebb08eed2a36b5f9143cbe8678edfaf25847086d4b1d35ebf77114655d9  -
38
```

Both symlink searches produced no output. The digest and count match the immutable archived review's
pre/post inventory. This check is evidence only that the staged prior build was not changed during
repair; it is not evidence that the repaired pack is correct.

## Final post-record audit

Commands:

```sh
set -eu
timeout 30s python3 sealed/validation/verify_artifact.py
cmp -s MANIFEST.yaml PRIOR_BUILD/MANIFEST.yaml
cmp -s PROVENANCE.json PRIOR_BUILD/PROVENANCE.json
printf 'PASS immutable JSON files match prior byte-for-byte\n'
printf 'scratch_or_bytecode_count='
find . \
    -path './PRIOR_BUILD' -prune -o \
    -path './PRIOR_REVIEW' -prune -o \
    -path './.agents' -prune -o \
    -path './.codex' -prune -o \
    \( -type d -name 'kafkalite-*' -o \
       -type f \( -name '*.class' -o -name '*.jar' -o -name '*.war' -o -name '*.pyc' \) \) \
    -print | wc -l
```

Observed exit 0 after this record was written:

```text
PASS required regular files: 23
PASS forbidden generated artifact paths: 0
PASS artifact entry types: regular files/directories only
PASS strict manifest/provenance object fingerprints
PASS status and labels: GENERATED + PARTIAL
PASS high-confidence credential scan: 0 hits
PASS archived Java build products: 0
PASS learner-view exact allowlist: 15 regular files, 0 sealed paths
PASS Java lexical structure: 8 source files
PASS immutable JSON files match prior byte-for-byte
scratch_or_bytecode_count=0
```

## Unperformed and inconclusive work

- Java 17 warnings-as-errors compilation and all Java test execution.
- Independent defensive-copy, atomicity, stale-first, boundary, model, concurrency, and fault tests.
- A positive validation of an actual harness-created sealed-free learner export.
- Fuzzing, benchmarking, profiling, load/soak, deployment, and security validation.
- External comparison with the linked `NOASSERTION` tutorial or the catalog checkout.

The linked material was not fetched or copied during repair. `LICENSE_BOUNDARY.md` keeps it outside
the generated-material CC0-1.0 grant.
