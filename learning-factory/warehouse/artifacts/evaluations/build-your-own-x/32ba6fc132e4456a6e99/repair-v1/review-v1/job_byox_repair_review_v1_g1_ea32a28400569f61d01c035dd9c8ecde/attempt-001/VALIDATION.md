# Independent validation record

Date: 2026-08-31  
Workspace: review attempt root  
Candidate policy: read-only

Every launcher invocation emitted host identity warnings saying that names could not be found for
UID 532319 and GID 500275. They did not alter the reported command statuses.

Inventory and learner-view commands below were run from the review attempt root. Commands whose
paths start at `public_tests/`, `sealed/`, or a root metadata filename were run from `CANDIDATE/`.

## 1. Inventory and immutability baseline

Command:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
find CANDIDATE -type f | wc -l
find CANDIDATE -type l -print
find CANDIDATE -not -type f -not -type d -print
```

Observed exit 0:

```text
756c53cd0c4967c36c5194fdc4256f6fbb9bbb6dc39de02c85b02bf8ab86c95b  -
40
```

Both entry-type searches produced no output. The digest is over the sorted `sha256sum` records,
including relative filenames. A final rerun reported the same digest and no test scratch directory.

## 2. Toolchain discovery

Command:

```sh
for review_tool in python3 sh timeout sha256sum mktemp dirname rm java javac git; do
    review_path=$(command -v "$review_tool" 2>/dev/null || true)
    if [ -n "$review_path" ]; then
        printf '%s=%s\n' "$review_tool" "$review_path"
    else
        printf '%s=UNAVAILABLE\n' "$review_tool"
    fi
done
python3 --version
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
```

`/tmp` was absent. Common JDK locations were absent or inaccessible; `ecj`, `jshell`, `jbang`,
Maven, and Gradle were also unavailable.

## 3. Parser and structural checks

Commands:

```sh
timeout 10s sh -n public_tests/run.sh
timeout 10s sh -n sealed/reference_tests/run.sh
python3 -c 'from pathlib import Path; paths=[Path("sealed/validation/verify_artifact.py"),Path("sealed/validation/verify_student_view.py")]; [compile(path.read_text(encoding="utf-8"), str(path), "exec") for path in paths]; print("PASS Python syntax:", len(paths))'
timeout 30s python3 sealed/validation/verify_artifact.py
```

Observed: both shell parses produced no output and exited 0. Python syntax compilation exited 0:

```text
PASS Python syntax: 2
```

The candidate-controlled structural verifier exited 0:

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
```

This is structural evidence only. In particular, its lexical Java check is not compilation.

## 4. Java runner attempts

Commands (the absolute review root was supplied as the writable temporary parent):

```sh
set +e
REVIEW_ROOT=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_v1_g1_ea32a28400569f61d01c035dd9c8ecde/attempt-001
TMPDIR="$REVIEW_ROOT" timeout 30s sh public_tests/run.sh
public_status=$?
printf 'public_runner_exit=%s\n' "$public_status"

TMPDIR="$REVIEW_ROOT" timeout 30s sh sealed/reference_tests/run.sh
reference_status=$?
printf 'reference_runner_exit=%s\n' "$reference_status"
```

Observed:

```text
public_tests/run.sh: line 30: javac: command not found
public_runner_exit=127
sealed/reference_tests/run.sh: line 30: javac: command not found
reference_runner_exit=127
```

Post-run searches found no `kafkalite-public-tests.*` or `kafkalite-reference-tests.*` directory,
so both traps cleaned their temporary directories. No Java source compiled and no Java case ran.

The documented invalid-temporary-directory path was also checked:

```sh
TMPDIR=environment/not-created timeout 10s sh public_tests/run.sh milestone-1
```

It exited 1, printed the following, and did not create that path:

```text
TMPDIR is not an existing writable directory: environment/not-created
```

## 5. Static contract and test inspection

Commands:

```sh
nl -ba README.md | sed -n '1,115p'
nl -ba REQUIREMENTS.md | sed -n '1,90p'
nl -ba starter/README.md | sed -n '38,66p'
nl -ba public_tests/README.md | sed -n '1,35p'
nl -ba public_tests/src/io/learningfactory/kafkalite/ContractTests.java | sed -n '1,220p'
nl -ba sealed/reference/src/main/java/io/learningfactory/kafkalite/ReplicatedPartition.java
nl -ba sealed/reference_tests/src/io/learningfactory/kafkalite/ReferenceTests.java
```

Observed:

- Ten public and fourteen sealed cases are registered. The sealed model loop is fixed at 1,024
  operations and is accurately described as model-based testing rather than fuzzing.
- Milestone 2's configuration case calls later fault/recovery methods at public-test lines 130-134.
  Milestone 3 calls recovery at lines 180-184 and 214-216, contrary to the promise that unfinished
  later work cannot obscure a selected group.
- The authoritative requirements at lines 40-41 require a deterministic initial leader but do not
  require the lowest ID. The starter guide and public assertion do require the lowest ID.
- Static review of the reference found a coherent reachable-state implementation of defensive
  copying, exclusive offsets, preflighted append rejection, sorted elections, and catch-up. This
  observation is inconclusive until a Java compiler and independent runtime tests are available.

## 6. Manifest and provenance consistency

Command:

```sh
python3 -c 'import json; from pathlib import Path; m=json.loads(Path("MANIFEST.yaml").read_text()); p=json.loads(Path("PROVENANCE.json").read_text()); print(m["project_id"] == p["project"]["project_id"]); print(m["source_id"] == p["project"]["source_id"] == p["source"]["source_id"]); print(m["source_commit"] == p["project"]["metadata"]["provenance"]["source_commit"] == p["source"]["commit_hash"]); print(m["provenance_sha256"] == p["snapshot_sha256"]); print(m["status"], m["validation_labels"], m["productionized"], m["independent_validation"])'
```

Observed exit 0:

```text
True
True
True
True
GENERATED ['GENERATED', 'PARTIAL'] False REQUIRED
```

The provenance object records the linked resource license as `NOASSERTION` and
`linked_content_copied` as false. The full-pack license prose preserves that boundary and grants
generated material under CC0. External similarity/no-copy verification was unavailable because the
source checkout, git, and network access were unavailable.

## 7. Learner-view boundary

A temporary directory under the writable review root was populated by copying exactly each line of
`CANDIDATE/environment/student-view-files.txt`. No candidate file was changed. Command applied to
construct and validate the view:

```sh
REVIEW_ROOT=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_v1_g1_ea32a28400569f61d01c035dd9c8ecde/attempt-001
review_view=$(mktemp -d "$REVIEW_ROOT/reviewer-student-view.XXXXXX")
trap 'rm -r -- "$review_view"' EXIT HUP INT TERM
while IFS= read -r relative_path; do
    destination_directory=$(dirname -- "$relative_path")
    mkdir -p -- "$review_view/$destination_directory"
    cp -- "CANDIDATE/$relative_path" "$review_view/$relative_path"
done < CANDIDATE/environment/student-view-files.txt
timeout 30s python3 CANDIDATE/sealed/validation/verify_student_view.py "$review_view"
```

Observed exit 0:

```text
PASS learner view: 15 regular files, 13 directories, exact hashes
```

Direct existence checks in that accepted view reported these omissions:

```text
LICENSE_BOUNDARY.md
PROVENANCE.json
VALIDATION.md
adversarial/README.md
benchmarks/README.md
debugging/README.md
review_exercises/README.md
```

The exercise omissions are documented policy. The first three are nevertheless linked from the
exported root README, so the accepted learner view contains dead references and lacks the explicit
license/provenance explanation. This reviewer-created copy is not an orchestrator-captured transfer
and does not establish `TRANSFER_VERIFIED`.

## 8. Dependency, credential, and product scans

Commands:

```sh
find . -type f -name '*.java' -exec grep -h '^import ' {} + | sort -u
find . -type f \( -name '*.class' -o -name '*.jar' -o -name '*.war' -o -name '*.pyc' \) -print
```

Observed: every import began with `java.`. The generated-product search produced no output. An
independent filename-only scan of all 40 regular files found zero private-key, AWS access-key,
GitHub token, or Slack token patterns. This limited scan is not a general security audit.

## 9. Inconclusive and unavailable checks

- Java 17 warnings-as-errors compilation and all public/sealed behavioral execution.
- Independent generated traces, concurrency checks, fuzzing, benchmarks, profiling, load/soak,
  security testing, deployment, or production-readiness validation.
- Comparison to the linked `NOASSERTION` tutorial or the catalog checkout.
- An orchestrator-created learner delivery and acceptance-validator capture.

No claim for `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
`PRODUCTIONIZED` follows from the checks above.
