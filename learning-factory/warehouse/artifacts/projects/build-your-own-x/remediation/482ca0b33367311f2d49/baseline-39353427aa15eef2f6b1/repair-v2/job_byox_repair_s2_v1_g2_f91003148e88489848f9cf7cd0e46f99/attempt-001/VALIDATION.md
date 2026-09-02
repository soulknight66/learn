# Repair validation evidence

Validation date: 2026-09-02 (America/Chicago). Commands ran from the repaired pack root. This is
repair generation 2 under policy version 1, against material baseline
`39353427aa15eef2f6b16b4e7269d0188c693facd5ed37e1efde8e603b24dcd7` and remediation snapshot
`6de45bc2529957726c7391a3db826b9d5eaef13829467834b3599f8846f93b29`. Prior build and review
results were not treated as current evidence; the observations below were reproduced in this
workspace after the repair.

The command wrapper emitted unrelated numeric UID/GID lookup warnings before commands. They did not
replace the captured child exit status.

## Toolchains

Commands:

```bash
/usr/bin/timeout 10s /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/timeout 10s /arm/tools/adoptopenjdk/openjdk/21.0.5_11/linux64/jdk-21.0.5+11/bin/java -version
```

Both exited `0`. Observed output:

```text
Python 3.11.5
openjdk version "21.0.5" 2024-10-15 LTS
OpenJDK Runtime Environment Temurin-21.0.5+11 (build 21.0.5+11-LTS)
OpenJDK 64-Bit Server VM Temurin-21.0.5+11 (build 21.0.5+11-LTS, mixed mode, sharing)
```

Java is configured but is not useful to this Python-only pack; no Java build was attempted. No
network access or dependency installation was attempted.

## Self-contained scratch sequence and syntax build

Scratch was absent at the start, created once beneath the existing `environment/` root, retained
through every test command, and removed only after the final suite. The exact setup and syntax command
were:

```bash
test ! -e environment/.validation-tmp
mkdir -p environment/.validation-tmp/compile environment/.validation-tmp/public \
  environment/.validation-tmp/sealed environment/.validation-tmp/starter \
  environment/.validation-tmp/custom
/usr/bin/timeout 30s env \
  PYTHONPYCACHEPREFIX=environment/.validation-tmp/compile \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m compileall -q -f starter public_tests sealed/reference sealed/reference_tests \
  environment/export_student_view.py
```

Setup and compilation exited `0`; `compileall` emitted no diagnostics. This setup is a required part
of the recipe, so no later `TMPDIR` names an absent directory.

## Repair regressions

Command:

```bash
/usr/bin/timeout 30s env \
  TMPDIR=environment/.validation-tmp/custom PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest -v \
  sealed.reference_tests.test_layers_private.PrivateLayerTests.test_invalid_derived_whiteout_target_is_rejected_without_mutation \
  sealed.reference_tests.test_layers_private.PrivateLayerTests.test_implicit_directory_modes_ignore_restrictive_umask \
  sealed.reference_tests.test_student_view_private.StudentViewBoundaryTests.test_learner_view_carries_generated_material_terms
```

Observed exit `0`:

```text
Ran 3 tests

OK
```

The first case applies `.wh.victim` followed by the invalid marker `.wh...` and asserts that
`PathEscape` occurs while the pre-existing victim still contains `preserve`. The second applies a
file through an implicit parent under umask `077` and asserts both destination and parent are `0755`.
The third requires the allowlisted learner notice to carry the grant, preservation direction, and
`NOASSERTION` boundary.

## Student-view boundary

The source-only check creates no learner workspace:

```bash
/usr/bin/timeout 10s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/export_student_view.py --source . --check
```

Observed exit `0` and exact output:

```json
{"files":28,"status":"ok"}
```

An additional plan and terms audit used this exact command:

```bash
/usr/bin/timeout 10s env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'from pathlib import Path; from environment.export_student_view import build_plan; paths=[relative.as_posix() for relative,_ in build_plan(Path("."))]; notice=Path("environment/COPYING_NOTICE.md").read_text(encoding="utf-8"); forbidden={"PROVENANCE.json","LICENSE_BOUNDARY.md","VALIDATION.md","sealed","adversarial","benchmarks","debugging","review_exercises"}; leaked=sorted(forbidden.intersection(path.split("/",1)[0] for path in paths)); terms=all(value in notice for value in ("permission is granted","CC0-1.0","NOASSERTION","Preserve this notice")); assert len(paths)==28 and "environment/COPYING_NOTICE.md" in paths and not leaked and terms; print(f"learner_files={len(paths)} copying_notice=true operative_terms=true evaluator_roots={leaked}")'
```

Observed exit `0` and exact output:

```text
learner_files=28 copying_notice=true operative_terms=true evaluator_roots=[]
```

The full evaluator provenance and boundary records remain excluded. The allowlisted learner-safe
notice carries the generated-material permissions and source/license boundary instead.

## Supplied suites

Public contract against the repaired sealed reference:

```bash
/usr/bin/timeout 30s env \
  TMPDIR=environment/.validation-tmp/public PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed exit `0`:

```text
Ran 11 tests

OK
```

Sealed evaluator suite:

```bash
/usr/bin/timeout 45s env \
  TMPDIR=environment/.validation-tmp/sealed PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=sealed/reference \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s sealed/reference_tests -v
```

Observed exit `0`:

```text
Ran 37 tests

OK
```

The sealed count includes the three repair regressions described above in addition to the prior
layer, path, image, SQLite, process, engine, CLI, and release-boundary cases.

Untouched learner starter against the public contract:

```bash
/usr/bin/timeout 30s env \
  TMPDIR=environment/.validation-tmp/starter PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=starter \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s public_tests -v
```

Observed exit `1`:

```text
Ran 11 tests

FAILED (errors=17)
```

All errors were explicit numbered starter `NotImplementedError` sites. This expected failure is
evidence that the learner starter was not replaced with the sealed implementation.

Only after all suite commands completed, scratch was removed and absence was checked:

```bash
find environment/.validation-tmp -depth -delete
test ! -e environment/.validation-tmp
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks \
  \( -name __pycache__ -o -name '*.pyc' -o -name '.validation-tmp' \) -print
```

All three commands exited `0`; the last command printed no path.

## Structure, immutable records, and preservation

Required and forbidden path audit:

```bash
env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'from pathlib import Path; required=["README.md","AGENTS.md","MANIFEST.yaml","PROVENANCE.json","LICENSE_BOUNDARY.md","REQUIREMENTS.md","CONCEPTS.md","DESIGN_QUESTIONS.md","VALIDATION.md","starter/README.md","public_tests/README.md","environment/README.md","sealed/reference/README.md","sealed/reference_tests/README.md","sealed/DESIGN.md","sealed/TRADEOFFS.md","sealed/REVIEW.md","sealed/alternatives/README.md","sealed/production/PRODUCTIONIZATION.md","adversarial/README.md","debugging/README.md","review_exercises/README.md","benchmarks/README.md"]; forbidden=[".git",".env",".venv","credentials.json","secrets","reference","reference_tests","hidden_tests","solution","solutions","answers","starter/sealed","starter/reference","starter/reference_tests","starter/solution","starter/solutions","starter/answers","public_tests/sealed","public_tests/reference","public_tests/hidden_tests","environment/sealed","LICENSE","ARTIFACT_INVENTORY.sha256"]; missing=[path for path in required if not Path(path).is_file()]; present=[path for path in forbidden if Path(path).exists()]; prior_missing=[path.relative_to("PRIOR_BUILD").as_posix() for path in Path("PRIOR_BUILD").rglob("*") if path.is_file() and not Path(*path.parts[1:]).is_file()]; assert not missing, missing; assert not present, present; assert not prior_missing, prior_missing; print(f"required_paths={len(required)} missing=0 forbidden_present=0 prior_files_preserved=true")'
```

Observed exit `0` and exact output:

```text
required_paths=23 missing=0 forbidden_present=0 prior_files_preserved=true
```

Record identity command:

```bash
env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import hashlib,json; expected={"independent_validation":"REQUIRED","productionized":False,"project_id":"project_d76f888c329de3f5823edf9ffcbe85c3","provenance_sha256":"f0e8e2f368bc51cc22d42f5110ca8eb24b407cef1cee1c0db9d70c5e657ce4e3","schema_version":1,"source_commit":"aa17439b62f384511a5561ce308e9598b94d8989","source_id":"source_eac489a34bed5db9a1f2a580b457bcef","status":"GENERATED","validation_labels":["GENERATED","PARTIAL"]}; manifest=json.load(open("MANIFEST.yaml",encoding="utf-8")); provenance_bytes=open("PROVENANCE.json","rb").read(); provenance=json.loads(provenance_bytes); assert manifest==expected; assert hashlib.sha256(provenance_bytes).hexdigest()=="266aadf01d684512a09ebed6ddd12fdbb424c6b2c27bb676147ce4df18d37705"; assert provenance["snapshot_sha256"]==expected["provenance_sha256"]; assert provenance["project"]["project_id"]==expected["project_id"]; print("manifest_exact=true provenance_exact_byte_hash=true identity_match=true labels=GENERATED,PARTIAL")'
sha256sum MANIFEST.yaml PROVENANCE.json
```

Both exited `0`. Observed output:

```text
manifest_exact=true provenance_exact_byte_hash=true identity_match=true labels=GENERATED,PARTIAL
4eb8b23f9c116db38a01876763e2e4f97e22c4219c9446bf949bb7e374c43123  MANIFEST.yaml
266aadf01d684512a09ebed6ddd12fdbb424c6b2c27bb676147ce4df18d37705  PROVENANCE.json
```

Regular-entry and file-count commands:

```bash
find README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md \
  CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed \
  adversarial debugging review_exercises benchmarks -mindepth 0 ! -type f ! -type d -print
find README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md \
  CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed \
  adversarial debugging review_exercises benchmarks -type f | wc -l
```

Both exited `0`; the first printed no path and the second printed `60`. The staged roots and
factory-owned workspace controls are outside these explicit challenge-pack paths and were not used as
output.

## Textual audits

Commands:

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

The two negated searches exited `0` with no match output. The cache/scratch search exited `0` and
printed no path. These bounded scans do not prove the absence of every dynamic call or encoded
credential.

## Limits and labels

No fuzz campaign, benchmark, profiler, real namespace/cgroup/seccomp isolation, elevated execution,
upstream fetch, transfer test, deployment, production security review, or hostile multi-tenant test
was performed. Read-only image modes and integrity checks are not an OS security boundary, and
filesystem publication is not transactionally atomic with SQLite across a machine crash. Therefore
`MANIFEST.yaml` remains honestly limited to `status: GENERATED`, validation labels `GENERATED` and
`PARTIAL`, `productionized: false`, and `independent_validation: REQUIRED`. Only a fresh independent
validator may assign further labels.
