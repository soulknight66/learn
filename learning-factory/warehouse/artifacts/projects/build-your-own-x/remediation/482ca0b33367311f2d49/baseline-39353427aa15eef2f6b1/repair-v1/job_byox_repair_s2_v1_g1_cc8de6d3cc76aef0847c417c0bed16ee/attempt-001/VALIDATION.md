# Repair validation evidence

Validation date: 2026-09-02 (America/Chicago). Commands ran from the repaired pack root. This is
repair generation 1 under policy version 1, against material baseline
`39353427aa15eef2f6b16b4e7269d0188c693facd5ed37e1efde8e603b24dcd7` and remediation snapshot
`1ad35d33367f80b94721dc2081505d4bb82e695d1326d3fb2b2d4743b59732f6`. Prior build/review results
were not treated as current evidence; every result below was observed in this workspace.

The command wrapper emitted these unrelated identity warnings before each command:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

They did not alter the recorded child exit codes.

## Toolchains

Commands:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Both exited `0`. Observed version output:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java is configured but is not useful to this Python-only pack; no Java build was attempted. No
network access or dependency installation was attempted.

## Scratch and syntax build

The system temp locations are not assumed writable. Scratch was created beneath the existing
`environment/` root and later removed:

```bash
mkdir -p environment/.validation-tmp
/usr/bin/timeout 30s env \
  PYTHONPYCACHEPREFIX=environment/.validation-tmp/pycache-final \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m compileall -q -f starter public_tests sealed/reference sealed/reference_tests \
  environment/export_student_view.py
find environment/.validation-tmp -depth -delete
```

All three commands exited `0`. `compileall` emitted no diagnostics. The final scratch removal emitted
no path output; subsequent cache and structure audits were performed after removal.

## Deterministic student-view boundary

Command:

```bash
/usr/bin/timeout 10s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/export_student_view.py --source . --check
```

Observed exit `0` and exact program output:

```json
{"files":27,"status":"ok"}
```

This mode validated the sorted exact-file allowlist, every path component, regular-file types, and
learner-visible roots without creating a student workspace. The sealed suite separately asserts that
the checked plan excludes `sealed/`, private tests, answers, instructor exercises, provenance review
records, licensing records, and validation evidence.

## Public contract against the repaired sealed reference

Command:

```bash
/usr/bin/timeout 30s env \
  TMPDIR=environment/.validation-tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed exit `0` and summary:

```text
Ran 11 tests in 2.484s

OK
```

The output-limit public case now requires the complete marker-bearing UTF-8 result to remain inside
the five-byte limit.

## Sealed evaluator suite

Command:

```bash
/usr/bin/timeout 45s env \
  TMPDIR=environment/.validation-tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed exit `0` and summary:

```text
Ran 34 tests in 5.894s

OK
```

The 34 cases include the prior path/layer, lifecycle, SQLite, image, runner, and CLI checks plus
repair regressions for a symlink in supplied destination ancestry; no whiteout before a deterministic
target-type rejection; stage/hash/apply byte identity; readonly published modes and integrity
recheck; a forced two-publication tag race with loser cleanup; marker-inclusive output limits;
injectable log scratch; explicit writable CLI cwd; and the student-view allowlist. The CLI child's
scrubbed environment omits `TMPDIR`; its inner runner still passed because capture placement is
explicit.

## Intentional starter baseline

Command:

```bash
/usr/bin/timeout 30s env \
  TMPDIR=environment/.validation-tmp PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed exit `1` and summary:

```text
Ran 11 tests in 0.111s

FAILED (errors=17)
```

All errors were explicit numbered starter `NotImplementedError` sites. This expected failure is
evidence that the learner starter was not replaced with the reference implementation.

## Structure, immutable records, and preservation

Required/forbidden/preservation command (the `forbidden` list also checks the two explicitly
prohibited inventory/license roots):

```bash
env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'from pathlib import Path; required=["README.md","AGENTS.md","MANIFEST.yaml","PROVENANCE.json","LICENSE_BOUNDARY.md","REQUIREMENTS.md","CONCEPTS.md","DESIGN_QUESTIONS.md","VALIDATION.md","starter/README.md","public_tests/README.md","environment/README.md","sealed/reference/README.md","sealed/reference_tests/README.md","sealed/DESIGN.md","sealed/TRADEOFFS.md","sealed/REVIEW.md","sealed/alternatives/README.md","sealed/production/PRODUCTIONIZATION.md","adversarial/README.md","debugging/README.md","review_exercises/README.md","benchmarks/README.md"]; forbidden=[".git",".env",".venv","credentials.json","secrets","reference","reference_tests","hidden_tests","solution","solutions","answers","starter/sealed","starter/reference","starter/reference_tests","starter/solution","starter/solutions","starter/answers","public_tests/sealed","public_tests/reference","public_tests/hidden_tests","environment/sealed","LICENSE","ARTIFACT_INVENTORY.sha256"]; missing=[p for p in required if not Path(p).is_file()]; present=[p for p in forbidden if Path(p).exists()]; prior_missing=[str(p.relative_to("PRIOR_BUILD")) for p in Path("PRIOR_BUILD").rglob("*") if p.is_file() and not Path(*p.parts[1:]).is_file()]; assert not missing, missing; assert not present, present; assert not prior_missing, prior_missing; print(f"required_paths={len(required)} missing=0 forbidden_present=0 prior_files_preserved=true")'
```

Observed exit `0` and exact result:

```text
required_paths=23 missing=0 forbidden_present=0 prior_files_preserved=true
```

Record identity command:

```bash
env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import hashlib,json; expected={"independent_validation":"REQUIRED","productionized":False,"project_id":"project_d76f888c329de3f5823edf9ffcbe85c3","provenance_sha256":"f0e8e2f368bc51cc22d42f5110ca8eb24b407cef1cee1c0db9d70c5e657ce4e3","schema_version":1,"source_commit":"aa17439b62f384511a5561ce308e9598b94d8989","source_id":"source_eac489a34bed5db9a1f2a580b457bcef","status":"GENERATED","validation_labels":["GENERATED","PARTIAL"]}; manifest=json.load(open("MANIFEST.yaml",encoding="utf-8")); provenance_bytes=open("PROVENANCE.json","rb").read(); provenance=json.loads(provenance_bytes); assert manifest==expected; assert hashlib.sha256(provenance_bytes).hexdigest()=="266aadf01d684512a09ebed6ddd12fdbb424c6b2c27bb676147ce4df18d37705"; assert provenance["snapshot_sha256"]==expected["provenance_sha256"]; assert provenance["project"]["project_id"]==expected["project_id"]; print("manifest_exact=true provenance_exact_byte_hash=true identity_match=true")'
sha256sum MANIFEST.yaml PROVENANCE.json
```

Both exited `0`. Observed output:

```text
manifest_exact=true provenance_exact_byte_hash=true identity_match=true
4eb8b23f9c116db38a01876763e2e4f97e22c4219c9446bf949bb7e374c43123  MANIFEST.yaml
266aadf01d684512a09ebed6ddd12fdbb424c6b2c27bb676147ce4df18d37705  PROVENANCE.json
```

The manifest `provenance_sha256` is a snapshot identifier, while the second hash above is the
`PROVENANCE.json` file-byte hash; `LICENSE_BOUNDARY.md` documents that distinction and the explicit
generated-material reuse terms. The factory-owned content inventory remains external as required.

Regular-entry and count commands:

```bash
find README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md \
  CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed \
  adversarial debugging review_exercises benchmarks -mindepth 0 ! -type f ! -type d -print
find README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md \
  CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed \
  adversarial debugging review_exercises benchmarks -type f | wc -l
```

Both exited `0`; the first printed no path and the second printed `59`. Thus all output entries are
regular files/directories. The staged `PRIOR_BUILD/` and `PRIOR_REVIEW/` roots are excluded from this
output count and were not modified. Factory-owned workspace controls `.agents`, `.codex`, and
`.factory-workspace` are likewise outside the challenge-pack output and were not modified.

## Textual audits

Commands and results are recorded after the final validation document was written:

```bash
! grep -RInE --include='*.py' '\.extract(all)?\(|shell[[:space:]]*=[[:space:]]*True' \
  starter sealed/reference
! grep -RInE --include='*.md' --include='*.py' --include='*.json' --include='*.yaml' \
  'AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|(password|passwd|api[_-]?key|access[_-]?token)[[:space:]]*[:=][[:space:]]*[^[:space:]]+' \
  README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md \
  CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed \
  adversarial debugging review_exercises benchmarks
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks \
  \( -name __pycache__ -o -name '*.pyc' -o -name '.validation-tmp' \) -print
```

The two negated searches exited `0` with no match output. The cache/scratch search exited `0` with no
path output. These bounded text scans do not prove the absence of every dynamic call or secret
encoding.

## Limits and labels

No fuzz campaign, benchmark, profiler, real namespace/cgroup/seccomp isolation, elevated execution,
upstream fetch, transfer test, deployment, production security review, or hostile multi-tenant test
was performed. Read-only modes plus integrity checks are not an OS security boundary, and filesystem
publication is not transactionally atomic with SQLite across a machine crash. Therefore
`MANIFEST.yaml` remains honestly limited to `status: GENERATED`, validation labels `GENERATED` and
`PARTIAL`, `productionized: false`, and `independent_validation: REQUIRED`. Only a fresh independent
validator may assign further labels.
