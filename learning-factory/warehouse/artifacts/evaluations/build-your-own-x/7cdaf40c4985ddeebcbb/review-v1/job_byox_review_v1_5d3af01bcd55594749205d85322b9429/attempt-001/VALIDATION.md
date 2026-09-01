# Independent validation record

Review date: 2026-08-31 (America/Chicago). All commands ran from the review
workspace root unless a command explicitly changes into `CANDIDATE`. The
candidate was inspected read-only and was not repaired.

## 1. Runtime and compiler availability

Command:

```bash
command -v java
command -v javac
java -version
javac -version
```

Observed:

- Both `command -v` checks produced no path and exited `1`.
- `java -version` and `javac -version` each exited `127` with `command not found`.
- `/usr/lib/jvm`, `/usr/share/java`, and `/opt` were absent.
- No `ecj`, `jikes`, `jshell`, `javap`, Maven, Gradle, Ant, `javalang`,
  `tree_sitter`, or `tree_sitter_java` substitute was available.
- System `python3 --version` reported `Python 3.6.8`; an available Python 3.11.5
  installation also lacked the Java parser modules.

Conclusion: Java compilation and JVM execution were unavailable.

## 2. Metadata parsing and provenance binding

Command:

```bash
python3 - <<'PY'
import hashlib, json
m = json.load(open('CANDIDATE/MANIFEST.yaml'))
p = json.load(open('CANDIDATE/PROVENANCE.json'))
actual = hashlib.sha256(open('CANDIDATE/PROVENANCE.json', 'rb').read()).hexdigest()
print('manifest_provenance_sha256=' + m['provenance_sha256'])
print('provenance_snapshot_sha256=' + p['snapshot_sha256'])
print('actual_file_sha256=' + actual)
print('declared_fields_match=' + str(m['provenance_sha256'] == p['snapshot_sha256']))
print('manifest_matches_file=' + str(m['provenance_sha256'] == actual))
print('ids_match=' + str(
    m['project_id'] == p['project']['project_id'] and
    m['source_id'] == p['project']['source_id'] and
    m['source_commit'] == p['source']['commit_hash']))
PY
```

Observed exit status: `0`.

```text
manifest_provenance_sha256=0577e5701f5f7125eb6b8c378a0607e95cd98d1253e257593d3b7e739a69319a
provenance_snapshot_sha256=0577e5701f5f7125eb6b8c378a0607e95cd98d1253e257593d3b7e739a69319a
actual_file_sha256=7945a3a2b470aff1edc4a632444e43ae0f44bf33b5f2511fc2f5c15e0e8e3797
declared_fields_match=True
manifest_matches_file=False
ids_match=True
```

Both metadata files parse as JSON. Project/source/commit identifiers are
internally consistent, and the manifest is honestly `GENERATED` + `PARTIAL`,
requires independent validation, and sets `productionized` to false. The
byte-level provenance binding fails.

## 3. Bounded runner attempts and immutability

The following logic computed a full sorted-file digest, wrapped each submitted
runner in an independent ten-second bound, and recomputed the digest:

```bash
set +e
tree_digest() {
  find CANDIDATE -type f -o -type l | LC_ALL=C sort |
    while IFS= read -r p; do sha256sum "$p"; done |
    sha256sum | awk '{print $1}'
}
before=$(tree_digest)
for script in ./environment/run-public-tests.sh \
              ./sealed/run-reference-tests.sh \
              ./sealed/run-benchmark.sh; do
  output=$(cd CANDIDATE && timeout 10s "$script" 2>&1)
  rc=$?
  echo "$script exit=$rc output=$output"
done
after=$(tree_digest)
echo "tree_before=$before"
echo "tree_after=$after"
[ "$before" = "$after" ]
echo "immutable_compare_exit=$?"
```

Observed:

```text
./environment/run-public-tests.sh exit=127 output=BLOCKED: javac is required (JDK 17+)
./sealed/run-reference-tests.sh exit=127 output=BLOCKED: javac is required (JDK 17+)
./sealed/run-benchmark.sh exit=127 output=BLOCKED: java and javac are required (JDK 17+)
tree_before=c3c9eb94a71f25b9695cf39ff6966d7349a621e4b4f4b5d22fd59cd34a7e1bb5
tree_after=c3c9eb94a71f25b9695cf39ff6966d7349a621e4b4f4b5d22fd59cd34a7e1bb5
immutable_compare_exit=0
```

No compilation, test execution, class loading, fuzzing, or benchmark sample was
observed. The candidate remained byte-for-byte unchanged.

## 4. Shell and Java text-level sanity

Command:

```bash
sh -n CANDIDATE/environment/run-public-tests.sh \
      CANDIDATE/sealed/run-reference-tests.sh \
      CANDIDATE/sealed/run-benchmark.sh
```

Observed exit status: `0`; no output.

A read-only Python scanner then walked all `.java` files. It ignored line and
block comments plus escaped string/character contents; checked `()[]{}` balance
and unterminated lexical states; matched package declarations to paths; and
matched public top-level type names to filenames.

Observed exit status: `0`.

```text
java_files 25
static_java_sanity PASS
```

This is only text-level evidence. It cannot detect Java type errors, lint
failures, class-file defects, verifier failures, or semantic errors.

## 5. Structure, disclosure, and credential signatures

Command (read-only `os.walk` plus five common credential regex classes):

```bash
python3 - <<'PY'
import os, re
root = 'CANDIDATE'
files = []
for base, dirs, names in os.walk(root, followlinks=False):
    for name in names:
        files.append(os.path.join(base, name))
symlinks = [p for p in files if os.path.islink(p)]
special = [p for p in files if not os.path.islink(p) and not os.path.isfile(p)]
sealed = [p for p in files if '/sealed/' in p or p.startswith(root + '/sealed/')]
patterns = {
    'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
    'aws_access': re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
    'github_token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b'),
    'openai_key': re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b'),
    'assigned_secret': re.compile(r'(?i)\b(?:password|secret|api[_-]?key)\b\s*[:=]\s*["\'][^"\']+["\']')
}
hits = []
for path in files:
    try:
        text = open(path, encoding='utf-8').read()
    except (UnicodeDecodeError, OSError):
        continue
    for label, pattern in patterns.items():
        if pattern.search(text):
            hits.append((label, path))
print('regular_file_count', len(files) - len(symlinks) - len(special))
print('symlinks', symlinks)
print('special', special)
print('sealed_files', len(sealed))
print('top_level_license_file', os.path.exists(root + '/LICENSE'))
print('credential_pattern_hits', hits)
PY
```

Observed exit status: `0`.

```text
regular_file_count 64
symlinks []
special []
sealed_files 24
top_level_license_file False
credential_pattern_hits []
```

The scan is limited to those signatures and is not proof that no secret exists.
The 24 sealed files include a complete reference implementation, reference
tests, answers, and review/design material. No produced learner view was supplied
for an end-to-end isolation check.

## 6. Runner bounds

Command:

```bash
for f in CANDIDATE/environment/run-public-tests.sh \
         CANDIDATE/sealed/run-reference-tests.sh \
         CANDIDATE/sealed/run-benchmark.sh; do
  if grep -Eq '(^|[^[:alnum:]_])(timeout|ulimit|setsid)([^[:alnum:]_]|$)' "$f"; then
    echo "$f: bound primitive present"
  else
    echo "$f: no timeout/resource/process-group primitive"
  fi
done
```

Observed exit status: `0`.

```text
CANDIDATE/environment/run-public-tests.sh: no timeout/resource/process-group primitive
CANDIDATE/sealed/run-reference-tests.sh: no timeout/resource/process-group primitive
CANDIDATE/sealed/run-benchmark.sh: no timeout/resource/process-group primitive
```

The scripts use deterministic source sorting and temporary build directories,
but safe validation depends on an outer harness to impose bounds, isolate the
process tree, and capture durable logs.

## 7. Provenance and licensing limits

Static inspection confirmed that the candidate consistently labels the linked
resource `NOASSERTION` and does not claim a copied upstream implementation. It
also contains no top-level license or SPDX grant for the generated artifact.
The cited upstream catalog checkout, its CC0 evidence, and the linked article
were not present in this workspace, and network access was not used. Accordingly,
origin and no-copy claims remain unverified declarations rather than independent
provenance evidence.

## Result

`REVISE`. Preserve `GENERATED` + `PARTIAL`. Do not award `BUILDS`, `TESTED`,
`FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`
from this review.
