# Validation record

## Outcome

Artifact status remains **GENERATED + PARTIAL**. Independent validation is still required. The implementation and test sources were completed, but this host has no Node.js-compatible runtime, so no JavaScript test, adversarial, or benchmark execution is claimed. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label was earned here.

All commands below were run from the repository root on 2026-08-31. Output is reproduced without invented successes.

## Runtime discovery

```text
$ node --version
/bin/bash: node: command not found
exit 127

$ npm --version
/bin/bash: npm: command not found
exit 127

$ python3 --version
Python 3.6.8
exit 0
```

The alternate-runtime check was:

```bash
command -v nodejs
command -v bun
command -v deno
command -v qjs
command -v js
```

Each command exited 1 with empty output. No dependency was downloaded and no network access was used.

## Intended executable checks and observed results

```text
$ node --test public_tests/*.test.js
/bin/bash: node: command not found
exit 127

$ node --test sealed/reference_tests/*.test.js
/bin/bash: node: command not found
exit 127

$ node adversarial/run.js
/bin/bash: node: command not found
exit 127

$ node benchmarks/router-benchmark.js
/bin/bash: node: command not found
exit 127
```

The public suite contains 21 `node:test` cases and the sealed suite contains 33. Those are source counts, not passing-test counts. The benchmark attempt produced no measurements; none are reported elsewhere in the artifact.

## Static metadata checks

These exact commands exited 0:

```bash
python3 -m json.tool MANIFEST.yaml >/dev/null
python3 -m json.tool PROVENANCE.json >/dev/null
python3 -m json.tool starter/package.json >/dev/null
python3 -m json.tool sealed/reference/package.json >/dev/null
```

Observed byte-level hashes after the immutable JSON was checked against the supplied objects:

```text
$ sha256sum MANIFEST.yaml PROVENANCE.json starter/package.json sealed/reference/package.json
a4529eb3613733b2930841b447d4495d38f6945c54363fb61cee0132207c8dbd  MANIFEST.yaml
dc328469b4988520ffa7a9d9f58e207914721720b1a6d93bac854dcad0796f05  PROVENANCE.json
7c9146726d251329f5828e93d4ba00dfb438c626f042edaf3441eecc9dd98650  starter/package.json
d72d3b5a395ae904abe5992346651a93e1b1b99289ddcc1ecf85a85c5aebd6a3  sealed/reference/package.json
exit 0
```

## Structural and safety checks

Final structure verification covered the authoritative required and forbidden lists, using `os.path.lexists` so a broken symlink could not evade a forbidden-path check. It also used `lstat` over only the generated artifact paths to reject symlinks and special files.

```text
$ python3 environment/verify-structure.py
PASS required paths: 23 regular files
PASS forbidden paths: 21 absent
PASS artifact node types: 62 files, 25 directories
PASS immutable metadata: strict JSON and expected SHA-256
exit 0
```

A filename-only credential scan checked high-confidence private-key and provider-token signatures. It intentionally requested filenames rather than matching contents:

```bash
grep -RIlE -- '-----BEGIN (RSA|EC|OPENSSH|DSA) PRIVATE KEY-----|AKIA[0-9A-Z]{16}|ASIA[0-9A-Z]{16}|github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|sk-(proj-)?[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}' README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks
```

Observed output was empty with grep exit 1, meaning no match. A second scan for credential-like assignments also produced no filenames:

```bash
grep -RIlE -- '(password|passwd|api[_-]?key|access[_-]?token|client[_-]?secret)[[:space:]]*[:=][[:space:]]*[^[:space:]]{8,}' README.md AGENTS.md MANIFEST.yaml PROVENANCE.json LICENSE_BOUNDARY.md REQUIREMENTS.md CONCEPTS.md DESIGN_QUESTIONS.md VALIDATION.md starter public_tests environment sealed adversarial debugging review_exercises benchmarks
```

Observed output was empty with grep exit 1. Finally, this filename scan exited 0 with empty output:

```bash
find starter public_tests environment sealed adversarial debugging review_exercises benchmarks -type f \( -iname '*.pem' -o -iname '*.key' -o -iname '*credential*' -o -iname '*secret*' \) -print
```

## Review boundary

The reference and harnesses received a separate static, line-specific cross-review for API consistency, dispatch/error state, request isolation, route grammar, HEAD behavior, response headers, absolute test deadlines, bounded buffering, and server cleanup. Findings were corrected before this record was finalized. This review was not execution and is not an independent `REVIEWED` label.
