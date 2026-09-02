# Validation evidence

Validation date: 2026-09-02 (America/Chicago). All commands ran from the repository root. This file
records local observations; independent validators, not this document, assign completion labels.

## Toolchain

Command:

```bash
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
```

Observed exit code: `0`. Observed version line: `Python 3.11.5`.

The exact interpreter is
`/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3`. The configured JDK was not invoked because
this is a Python-only artifact with no Java source or build step. No dependency installation or
network access was attempted.

The command wrapper also emitted three environment identity warnings on stderr before commands:
`/usr/bin/id: cannot find name for user ID 532319`,
`/usr/bin/id: cannot find name for group ID 500275`, then the user warning again. They did not change
the recorded process exit codes.

## Syntax build

Command:

```bash
env PYTHONPYCACHEPREFIX=.validation-pycache /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m compileall -q -f starter public_tests sealed/reference sealed/reference_tests
```

Observed exit code: `0`; `compileall` emitted no diagnostics. The generated cache directory was scratch
and was explicitly removed before packaging.

## Public contract against the sealed reference

Command:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed exit code: `0`. Exact unittest summary:

```text
Ran 11 tests in 0.598s

OK
```

The passing cases covered path normalization, containment, traversal preflight, link rejection,
whiteouts, mode normalization, snapshot independence, lifecycle execution, log truncation, and
timeout status.

## Sealed evaluator suite

Command:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed/reference /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
```

Observed exit code: `0`. Exact unittest summary:

```text
Ran 25 tests in 3.806s

OK
```

Additional observations included duplicate/special tar rejection, byte quotas, opaque whiteouts,
strict modes, malformed archives, content-order digests, tag conflicts, failed-build cleanup, direct
trigger enforcement, two-thread atomic claims, corrupt JSON rejection, controlled environments,
invalid UTF-8 replacement, durable launch failure, and a full canonical-JSON CLI lifecycle.

## Intentional starter baseline

Command:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=starter /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
```

Observed exit code: `1`. Exact unittest summary:

```text
Ran 11 tests in 0.079s

FAILED (errors=17)
```

Every error was an explicit numbered `NotImplementedError` from the progressive starter (one test's
seven subtests account for the error count exceeding the test count). This failure is expected and is
preserved as evidence that the learner workspace does not contain the reference implementation.

## Packaging audits

Required and forbidden path command:

```bash
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'from pathlib import Path; required=["README.md","AGENTS.md","MANIFEST.yaml","PROVENANCE.json","LICENSE_BOUNDARY.md","REQUIREMENTS.md","CONCEPTS.md","DESIGN_QUESTIONS.md","VALIDATION.md","starter/README.md","public_tests/README.md","environment/README.md","sealed/reference/README.md","sealed/reference_tests/README.md","sealed/DESIGN.md","sealed/TRADEOFFS.md","sealed/REVIEW.md","sealed/alternatives/README.md","sealed/production/PRODUCTIONIZATION.md","adversarial/README.md","debugging/README.md","review_exercises/README.md","benchmarks/README.md"]; forbidden=[".git",".env",".venv","credentials.json","secrets","reference","reference_tests","hidden_tests","solution","solutions","answers","starter/sealed","starter/reference","starter/reference_tests","starter/solution","starter/solutions","starter/answers","public_tests/sealed","public_tests/reference","public_tests/hidden_tests","environment/sealed"]; missing=[p for p in required if not Path(p).is_file()]; present=[p for p in forbidden if Path(p).exists()]; assert not missing, missing; assert not present, present; print(f"required_paths={len(required)} missing=0 forbidden_present=0")'
```

Observed exit code: `0`. Exact result: `required_paths=23 missing=0 forbidden_present=0`.

JSON identity command:

```bash
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import json; manifest=json.load(open("MANIFEST.yaml",encoding="utf-8")); expected={"independent_validation":"REQUIRED","productionized":False,"project_id":"project_d76f888c329de3f5823edf9ffcbe85c3","provenance_sha256":"f0e8e2f368bc51cc22d42f5110ca8eb24b407cef1cee1c0db9d70c5e657ce4e3","schema_version":1,"source_commit":"aa17439b62f384511a5561ce308e9598b94d8989","source_id":"source_eac489a34bed5db9a1f2a580b457bcef","status":"GENERATED","validation_labels":["GENERATED","PARTIAL"]}; assert manifest==expected; provenance=json.load(open("PROVENANCE.json",encoding="utf-8")); assert set(provenance)=={"classification","license_boundary","material_baseline_sha256","project","schema_version","snapshot_sha256","source"}; assert provenance["snapshot_sha256"]==expected["provenance_sha256"]; assert provenance["project"]["project_id"]==expected["project_id"]; assert provenance["source"]["commit_hash"]==expected["source_commit"]; print("manifest_exact=true provenance_json_valid=true provenance_identity_fields=true")'
```

Observed exit code: `0`. Exact result:
`manifest_exact=true provenance_json_valid=true provenance_identity_fields=true`.
`sha256sum MANIFEST.yaml PROVENANCE.json` observed byte hashes
`4eb8b23f9c116db38a01876763e2e4f97e22c4219c9446bf949bb7e374c43123` and
`266aadf01d684512a09ebed6ddd12fdbb424c6b2c27bb676147ce4df18d37705`, respectively.

Regular-entry command:

```bash
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks -mindepth 1 ! -type f ! -type d -print
```

Observed exit code: `0` and no path output. Thus the generated trees contain directories and regular
files only; there are no archived symbolic links or special entries.

Cache command:

```bash
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks -name __pycache__ -o -name '*.pyc' -o -name '.validation-pycache'
```

Observed exit code: `0` and no path output after explicitly removing the four build-generated cache
directories.

Credential-pattern command:

```bash
! grep -RInE --include='*.md' --include='*.py' --include='*.json' --include='*.yaml' 'AKIA[0-9A-Z]{16}|-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----|(password|passwd|api[_-]?key|access[_-]?token)[[:space:]]*[:=][[:space:]]*[^[:space:]]+' README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks
```

Observed exit code: `0` from the negated search and no match output. Forbidden credential-like
filenames were also part of the exact-path audit. This is a pattern scan, not a guarantee about every
possible encoding.

## Limits and label

No benchmark, fuzz campaign, real namespace/cgroup/seccomp isolation, elevated execution, upstream
fetch, profiler run, transfer test, or production deployment was performed. Subprocess `cwd` and
environment changes are not a host security boundary. Therefore `MANIFEST.yaml` intentionally remains
`status: GENERATED`, with only `GENERATED` and `PARTIAL`, `productionized: false`, and independent
validation required.
