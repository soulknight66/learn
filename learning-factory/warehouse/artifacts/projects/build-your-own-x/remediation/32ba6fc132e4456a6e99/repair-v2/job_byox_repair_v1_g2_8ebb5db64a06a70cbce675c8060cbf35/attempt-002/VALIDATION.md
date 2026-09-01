# Repair validation record

Date: 2026-09-01  
Repair generation: 2  
Working directory: challenge-pack root

## Outcome and label boundary

This repaired pack remains **GENERATED + PARTIAL** and requires fresh independent validation. The
host-supported structural and source-consistency checks passed. The Java runners reached `javac`,
but this host has neither `javac` nor `java`; no Java source compiled and none of the 12 public or 14
sealed cases ran.

No learner workspace was created. The exact 15-file export allowlist remains sealed-free. Its root
README is now self-contained about provenance, CC0, the linked resource's `NOASSERTION` boundary,
and the lack of executable validation. A negative check against the existing `environment/`
directory confirmed that the learner-view validator rejects a non-view inventory. This is not
positive transfer evidence.

The repaired public source registers independent groups of 4, 2, 3, and 3 cases. Milestone 2 no
longer invokes fault, availability, replica-inspection, or recovery APIs; milestone 3 no longer
invokes recovery. `REQUIREMENTS.md` now makes the lowest-ID initial-leader rule authoritative. These
facts were checked structurally; without a JDK they are not behavioral test results.

Nothing here establishes `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

Every command launcher emitted these host identity warnings before the captured command output:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

## Toolchain discovery

Command:

```sh
for repair_tool in python3 sh timeout sha256sum mktemp dirname rm java javac git; do
    repair_path=$(command -v "$repair_tool" 2>/dev/null || true)
    if [ -n "$repair_path" ]; then
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
git=UNAVAILABLE
Python 3.6.8
/tmp=absent
```

## Script parsing and deterministic structural checks

Command:

```sh
set +e
timeout 10s sh -n public_tests/run.sh
public_shell_status=$?
printf 'public_shell_syntax_exit=%s\n' "$public_shell_status"
timeout 10s sh -n sealed/reference_tests/run.sh
sealed_shell_status=$?
printf 'sealed_shell_syntax_exit=%s\n' "$sealed_shell_status"
python3 -c 'from pathlib import Path; paths=[Path("sealed/validation/verify_artifact.py"),Path("sealed/validation/verify_student_view.py")]; [compile(path.read_text(encoding="utf-8"), str(path), "exec") for path in paths]; print("PASS Python syntax:", len(paths))'
python_syntax_status=$?
printf 'python_syntax_exit=%s\n' "$python_syntax_status"
timeout 30s python3 sealed/validation/verify_artifact.py
artifact_status=$?
printf 'artifact_verifier_exit=%s\n' "$artifact_status"
```

Observed output and statuses:

```text
public_shell_syntax_exit=0
sealed_shell_syntax_exit=0
PASS Python syntax: 2
python_syntax_exit=0
PASS required regular files: 23
PASS forbidden generated artifact paths: 0
PASS artifact entry types: regular files/directories only
PASS strict manifest/provenance object fingerprints
PASS status and labels: GENERATED + PARTIAL
PASS high-confidence credential scan: 0 hits
PASS archived Java build products: 0
PASS learner-view exact allowlist: 15 regular files, 0 sealed paths
PASS learner-visible contract: lowest-ID leader and self-contained license notice
PASS public milestone isolation: 4/2/3/3 cases
PASS Java lexical structure: 8 source files
artifact_verifier_exit=0
```

The milestone and Java checks above inspect source structure; they do not compile Java or execute a
case. The credential scan checks selected high-confidence private-key and assigned-token patterns,
not every possible secret format.

## Java runner attempts

Command:

```sh
set +e
unset TMPDIR
timeout 30s sh public_tests/run.sh milestone-1
public_runner_status=$?
printf 'public_runner_exit=%s\n' "$public_runner_status"
timeout 30s sh sealed/reference_tests/run.sh
sealed_runner_status=$?
printf 'sealed_runner_exit=%s\n' "$sealed_runner_status"
printf 'scratch_directories_after_attempts='
find . -maxdepth 1 -type d \
    \( -name 'kafkalite-public-tests.*' -o -name 'kafkalite-reference-tests.*' \) \
    -print | wc -l
```

Observed output:

```text
public_tests/run.sh: line 30: javac: command not found
public_runner_exit=127
sealed/reference_tests/run.sh: line 30: javac: command not found
sealed_runner_exit=127
scratch_directories_after_attempts=0
```

Because `/tmp` was absent and `TMPDIR` was unset, both runners used their repository-root fallback,
then their traps removed the generated scratch directories. Compilation and all behavioral cases
remain inconclusive.

## Invalid temporary-directory behavior

Command:

```sh
set +e
if [ -e environment/not-created ]; then
    printf 'precondition_unexpected_path_exists\n'
else
    printf 'precondition_invalid_tmpdir_absent\n'
fi
TMPDIR=environment/not-created timeout 10s sh public_tests/run.sh milestone-1
invalid_tmpdir_status=$?
printf 'invalid_tmpdir_exit=%s\n' "$invalid_tmpdir_status"
if [ -e environment/not-created ]; then
    printf 'postcondition_unexpected_path_exists\n'
else
    printf 'postcondition_invalid_tmpdir_absent\n'
fi
```

Observed expected rejection:

```text
precondition_invalid_tmpdir_absent
TMPDIR is not an existing writable directory: environment/not-created
invalid_tmpdir_exit=1
postcondition_invalid_tmpdir_absent
```

## Learner-view validator negative check

No learner view was created. The validator was pointed at the already existing `environment/`
directory to exercise its fail-closed inventory check.

Command:

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

A delivery harness must copy exactly the allowlisted files into an external view and invoke the
sealed validator there. No positive export was created or validated in this job.

## Manifest and provenance consistency

Command:

```sh
set +e
cmp -s MANIFEST.yaml PRIOR_BUILD/MANIFEST.yaml
manifest_cmp_status=$?
printf 'manifest_prior_byte_compare_exit=%s\n' "$manifest_cmp_status"
cmp -s PROVENANCE.json PRIOR_BUILD/PROVENANCE.json
provenance_cmp_status=$?
printf 'provenance_prior_byte_compare_exit=%s\n' "$provenance_cmp_status"
sha256sum MANIFEST.yaml PROVENANCE.json
python3 -c 'import json; from pathlib import Path; m=json.loads(Path("MANIFEST.yaml").read_text()); p=json.loads(Path("PROVENANCE.json").read_text()); print(m["project_id"] == p["project"]["project_id"]); print(m["source_id"] == p["project"]["source_id"] == p["source"]["source_id"]); print(m["source_commit"] == p["project"]["metadata"]["provenance"]["source_commit"] == p["source"]["commit_hash"]); print(m["provenance_sha256"] == p["snapshot_sha256"]); print(m["status"], m["validation_labels"], m["productionized"], m["independent_validation"])'
```

Observed exit 0:

```text
manifest_prior_byte_compare_exit=0
provenance_prior_byte_compare_exit=0
3bf839882001eb0ef2f7aeb7f438c8adfa18d939c79b1002ac22ccdae9ec9e37  MANIFEST.yaml
2919bdf8ee18e125b4bc790b79d98781687337f9c7b522c6a9f6a8e248432dc9  PROVENANCE.json
True
True
True
True
GENERATED ['GENERATED', 'PARTIAL'] False REQUIRED
```

The structural verifier separately parsed both as strict JSON and checked their canonical object
hashes against the job-bound fingerprints.

## Staged-root immutability check

The prior-build filename prefix was normalized to `CANDIDATE/`, matching the archived review's
digest convention. Both digests also match the values observed before copying the prior top-level
entries.

Command:

```sh
printf 'prior_build_normalized_digest='
find PRIOR_BUILD -type f -print0 | sort -z | xargs -0 sha256sum \
    | sed 's#  PRIOR_BUILD/#  CANDIDATE/#' | sha256sum | cut -d' ' -f1
printf 'prior_build_file_count='
find PRIOR_BUILD -type f | wc -l
printf 'prior_review_digest='
find PRIOR_REVIEW -type f -print0 | sort -z | xargs -0 sha256sum \
    | sha256sum | cut -d' ' -f1
printf 'prior_review_file_count='
find PRIOR_REVIEW -type f | wc -l
printf 'staged_symlink_count='
find PRIOR_BUILD PRIOR_REVIEW -type l -print | wc -l
```

Observed exit 0:

```text
prior_build_normalized_digest=756c53cd0c4967c36c5194fdc4256f6fbb9bbb6dc39de02c85b02bf8ab86c95b
prior_build_file_count=40
prior_review_digest=8ee10aec0f2b6c0d91de03b935ce033fc6545daabcccd4c85c90df3edc8b73a1
prior_review_file_count=3
staged_symlink_count=0
```

## Unperformed and inconclusive work

- Java 17 warnings-as-errors compilation and all public/sealed behavioral execution.
- Independent generated traces, concurrency checks, fuzzing, benchmarking, profiling, load/soak,
  security testing, deployment, or production-readiness validation.
- Positive validation of a harness-created learner export.
- External comparison with the linked `NOASSERTION` tutorial or catalog checkout; `git` and network
  source access were unavailable.

Fresh independent validation remains mandatory.
