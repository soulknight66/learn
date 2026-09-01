# Validation record

This record reports only commands actually run in the allocated workspace on 2026-08-31. The
authoritative labels remain `GENERATED` and `PARTIAL`; independent validation is required.

## Runtime availability

```text
$ python3 --version
Python 3.11.5

$ node --version
/bin/bash: node: command not found
exit 127
```

The combined visible/reference test command was attempted:

```text
$ node --test public_tests/*.test.mjs sealed/reference_tests/*.test.mjs
/bin/bash: node: command not found
exit 127
```

Consequently no JavaScript test, adversarial case, fuzz campaign, or benchmark was executed. There
are no pass counts, coverage values, timings, or performance claims to report. The benchmark harness
must remain gated on successful correctness tests.

## Deterministic checks

The reusable checker is `sealed/validation/check_artifact.py`. It parses strict JSON while rejecting
duplicate keys, checks canonical hashes for both immutable supplied objects, compares the manifest
object exactly, inspects paths and file types, resolves JavaScript imports, rejects dynamic host-code
mechanisms, and scans high-confidence credential patterns.

```text
$ python3 sealed/validation/check_artifact.py
required paths: 23/23 present
raw forbidden paths present: ['.git']
artifact forbidden paths present: []
artifact path types: regular files/directories only
metadata: strict JSON, exact manifest, immutable object hashes match
JavaScript modules: 26 files, 46 relative imports resolved
credential scan: 68 files, 0 high-confidence matches
STATIC VALIDATION PASS
exit 0
```

The static pass does not promote the artifact beyond `PARTIAL`. A manual authoring review is recorded
in `sealed/REVIEW.md`; it likewise is not an independent review label. Manual boundary review found
no reference implementation, answer key, or solution-bearing review content in `starter/`,
`public_tests/`, or `environment/`; all such material is rooted under `sealed/`. Later-stage prompt
directories still require the administrator's configured reveal policy.

## Scope note

The workspace is provisioned with platform-owned control entries, including `.git`, `.agents`,
`.codex`, `.factory-workspace`, and `JOB.md`. They were not created, read as project content,
modified, or included in artifact-relative checks. The raw workspace therefore still contains a
pre-existing `.git` despite `.git` being forbidden as an artifact path; the generated archive/view
must exclude those control entries. All path statements below refer to the generated artifact
roots, not those platform-owned entries.
