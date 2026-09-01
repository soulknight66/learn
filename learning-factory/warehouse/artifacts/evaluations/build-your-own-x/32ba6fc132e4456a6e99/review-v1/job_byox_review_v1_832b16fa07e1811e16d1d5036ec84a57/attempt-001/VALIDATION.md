# Independent validation record

Review date: 2026-08-31  
Workspace: independent review attempt 001  
Candidate policy: read-only; no candidate file was edited.

Recurring `/usr/bin/id` warnings about unmapped sandbox IDs are environment noise and are omitted
from excerpts below.

## 1. Inventory and immutability

Command, run before and after all candidate checks:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Both observations were identical (exit `0`):

```text
9d6c0ebb08eed2a36b5f9143cbe8678edfaf25847086d4b1d35ebf77114655d9  -
```

Additional inventory commands:

```sh
find CANDIDATE -type f | wc -l
find CANDIDATE -type l -o -type p -o -type s -o -type b -o -type c
find CANDIDATE -printf '%m %y %p\n' | sort
```

Observed: 38 regular files, no irregular entries printed, all regular files mode `0444`, and all
directories mode `2555`.

## 2. Toolchain discovery

Commands and results:

```sh
java -version
# exit 127: /bin/bash: java: command not found

javac -version
# exit 127: /bin/bash: javac: command not found

python3 --version
# exit 0: Python 3.6.8

/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
# exit 0: Python 3.11.5
```

No `jshell`, `ecj`, `javap`, `jar`, `mvn`, `gradle`, `ant`, `jbang`, or Java parser Python package
was found. Therefore no Java compilation or execution result exists.

## 3. Shell runners

Syntax check:

```sh
cd CANDIDATE
sh -n public_tests/run.sh
sh -n sealed/reference_tests/run.sh
```

Each exited `0` with no output.

Documented commands with the default environment:

```sh
sh public_tests/run.sh
sh sealed/reference_tests/run.sh
```

Each exited `1` before invoking `javac`:

```text
mktemp: failed to create directory via template ‘/tmp/kafkalite-public-tests.XXXXXX’: No such file or directory
mktemp: failed to create directory via template ‘/tmp/kafkalite-reference-tests.XXXXXX’: No such file or directory
```

`ls -ld /tmp` independently reported that `/tmp` does not exist. Controlled retries directed scratch
outside `CANDIDATE/`:

```sh
TMPDIR="$PWD/.." sh public_tests/run.sh
TMPDIR="$PWD/.." sh sealed/reference_tests/run.sh
```

Both reached line 13 and exited `127`:

```text
public_tests/run.sh: line 13: javac: command not found
sealed/reference_tests/run.sh: line 13: javac: command not found
```

Their traps removed the temporary directories. These are environment limitations, not Java test
failures.

## 4. Structural verifier

The documented command used PATH Python 3.6.8:

```sh
cd CANDIDATE
python3 sealed/validation/verify_artifact.py
```

Observed exit `1`:

```text
File "sealed/validation/verify_artifact.py", line 4
  from __future__ import annotations
SyntaxError: future feature annotations is not defined
```

Retry with the available Python 3.11.5:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/validation/verify_artifact.py
```

Observed exit `0`:

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

Unlike the builder's historical record, the archived candidate has no `.git` entry, so the verifier
did not print its conditional `.git` note.

## 5. Independent verifier mutation check

A reviewer-owned scratch copy was created outside `CANDIDATE/`. Its copied mode bits were made
writable, all `*.java` and `run.sh` files were moved outside the copied artifact, the candidate's
unmodified verifier was run against that incomplete copy, and the entire scratch directory was
removed:

```sh
review_tmp=$(mktemp -d "$PWD/reviewer-verifier-copy.XXXXXX")
case "$review_tmp" in "$PWD"/reviewer-verifier-copy.*) ;; *) exit 2 ;; esac
cleanup() {
    chmod -R u+w -- "$review_tmp" 2>/dev/null || true
    find "$review_tmp" -depth -delete
}
trap cleanup EXIT HUP INT TERM
mkdir "$review_tmp/artifact" "$review_tmp/quarantine"
cp -R CANDIDATE/. "$review_tmp/artifact/"
chmod -R u+w -- "$review_tmp/artifact"
item_number=0
find "$review_tmp/artifact" -type f \( -name '*.java' -o -name 'run.sh' \) -print |
while IFS= read -r source_file; do
    mv -- "$source_file" "$review_tmp/quarantine/$item_number.removed"
    item_number=$((item_number + 1))
done
printf 'remaining_java_files='
find "$review_tmp/artifact" -type f -name '*.java' | wc -l
printf 'remaining_runner_files='
find "$review_tmp/artifact" -type f -name 'run.sh' | wc -l
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
    "$review_tmp/artifact/sealed/validation/verify_artifact.py"
```

Observed counts and exit `0`:

```text
remaining_java_files=0
remaining_runner_files=0
PASS required regular files: 23
PASS forbidden generated artifact paths: 0
PASS artifact entry types: regular files/directories only
PASS strict manifest/provenance object fingerprints
PASS status and labels: GENERATED + PARTIAL
PASS high-confidence credential scan: 0 hits
PASS archived Java build products: 0
PASS Java lexical structure: 0 source files
```

This demonstrates that the verifier does not enforce the core source/test/runner inventory. No
candidate path was changed, and a final scratch search returned empty.

## 6. Independent metadata and source inventory

A Python 3.11 strict JSON check rejected duplicate keys/non-finite constants, asserted ID and commit
agreement across the two metadata objects, and inventoried Java imports. Raw hashes were also
computed with `sha256sum`.

Command (from the review root):

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 - <<'PY'
from pathlib import Path
import hashlib, json, re

root = Path("CANDIDATE")

def strict(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key {key!r}")
            result[key] = value
        return result
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError(f"non-finite constant {value}")
        ),
    )

manifest = strict(root / "MANIFEST.yaml")
provenance = strict(root / "PROVENANCE.json")
assert manifest["project_id"] == provenance["project"]["project_id"]
assert manifest["source_id"] == provenance["project"]["source_id"] == provenance["source"]["source_id"]
assert manifest["source_commit"] == provenance["source"]["commit_hash"]
assert manifest["status"] == "GENERATED"
assert manifest["validation_labels"] == ["GENERATED", "PARTIAL"]
assert manifest["productionized"] is False
files = [path for path in root.rglob("*") if path.is_file()]
symlinks = [path for path in root.rglob("*") if path.is_symlink()]
imports = []
for path in root.rglob("*.java"):
    imports += re.findall(r"^import\s+([^;]+);", path.read_text(), re.MULTILINE)
assert all(name.startswith("java.") for name in imports)
print("strict_json=PASS")
print("id_commit_consistency=PASS")
print("labels=GENERATED,PARTIAL productionized=false")
print(f"regular_files={len(files)} symlinks={len(symlinks)}")
print(f"java_sources={sum(1 for _ in root.rglob('*.java'))} imports={len(imports)} non_java_imports=0")
for name in ("MANIFEST.yaml", "PROVENANCE.json"):
    value = strict(root / name)
    raw = hashlib.sha256((root / name).read_bytes()).hexdigest()
    canonical = hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()).hexdigest()
    print(f"{name} raw_sha256={raw} canonical_sha256={canonical}")
print(f"manifest_provenance_sha256={manifest['provenance_sha256']}")
PY
```

Observed exit `0` and summary:

```text
strict_json=PASS
id_commit_consistency=PASS
labels=GENERATED,PARTIAL productionized=false
regular_files=38 symlinks=0
java_sources=8 imports=23 non_java_imports=0
MANIFEST.yaml raw_sha256=3bf839882001eb0ef2f7aeb7f438c8adfa18d939c79b1002ac22ccdae9ec9e37
MANIFEST.yaml canonical_sha256=0189d1bdb1e7dc36f63c14bb6ff334a9bab5b0b182423a44a47d97a4b7a51df8
PROVENANCE.json raw_sha256=2919bdf8ee18e125b4bc790b79d98781687337f9c7b522c6a9f6a8e248432dc9
PROVENANCE.json canonical_sha256=62094b8a14e6bcdd9deb3dd67888b4a96489872debc725ad2f96e04379168fb4
manifest_provenance_sha256=a7356b40000cfd5a88331dd0bdf398d0834bf2552479e75be315415c0e9bdd57
```

The manifest value equals `PROVENANCE.snapshot_sha256`, not either digest of the provenance file.
Without an included schema, its semantics are inconclusive.

## 7. Static correctness and coverage inspection

The public and sealed case counts were obtained with:

```sh
cd CANDIDATE
grep -c '^[[:space:]]*run("' public_tests/src/io/learningfactory/kafkalite/ContractTests.java
# 10
grep -c '^[[:space:]]*run("' sealed/reference_tests/src/io/learningfactory/kafkalite/ReferenceTests.java
# 13
```

Manual, line-numbered inspection covered all starter/reference Java sources, both suites, runners,
requirements, and design/recovery documents. Observed:

- required starter and reference constructor/method signatures align;
- all 23 imports use `java.*` packages;
- static reference transitions appear coherent for reachable append, rejection, read, leader loss,
  all-down recovery, stale-first recovery, catch-up, idempotence, and defensive-copy paths;
- public expectations missing from the declared authoritative contract and stricter sealed
  collection-mutability expectations are detailed in `REVIEW.md`;
- the sealed “long” trace is a fixed sequence of roughly 13 state-changing calls, not generated or
  fuzz evidence.

Static reading and case counts do not prove compilation, execution, or correctness.

## 8. Claims, provenance, and boundaries

Text and path scans found no affirmative `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED` claim. The only occurrences disclaim those labels. No
external Java import, archived JVM product, symlink, or obvious high-confidence credential pattern
was observed.

The linked tutorial and upstream catalog were not available in the review sandbox. Consequently,
the source-license evidence, recorded upstream hashes, and the assertion that linked expression was
not copied or closely paraphrased remain independently unverified.

## Result

`REVISE`. No build/test/fuzz/benchmark/review/transfer/production label is earned by these checks,
and `CANDIDATE/MANIFEST.yaml` was not edited or promoted.
