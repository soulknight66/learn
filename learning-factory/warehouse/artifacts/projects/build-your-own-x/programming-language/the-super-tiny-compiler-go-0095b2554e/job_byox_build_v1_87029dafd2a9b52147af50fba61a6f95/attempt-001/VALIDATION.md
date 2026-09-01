# Generation validation record

Status remains **GENERATED + PARTIAL**. Independent validation is required. The observations below were made on the generation host on 2026-08-31; they do not assign `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

## Go toolchain discovery

Working directory: repository root.

```bash
go version
```

Observed exit status: `127`.

```text
/bin/bash: go: command not found
```

Neither `gofmt`, `gccgo`, `tinygo`, `gotip`, `gopls`, nor `goimports` was found through the host `PATH`. No toolchain or module was downloaded.

## Attempted Go tests

Each command was executed with the stated working directory. Every attempt exited `127` with the same literal output, so none compiled or ran tests.

| Working directory | Exact command | Exit | Observed output |
| --- | --- | ---: | --- |
| `starter/` | `GOTOOLCHAIN=local go test ./...` | 127 | `/bin/bash: go: command not found` |
| `public_tests/` | `GOTOOLCHAIN=local go test ./...` | 127 | `/bin/bash: go: command not found` |
| `sealed/reference/` | `GOTOOLCHAIN=local go test ./...` | 127 | `/bin/bash: go: command not found` |
| `sealed/reference_tests/` | `GOTOOLCHAIN=local go test ./...` | 127 | `/bin/bash: go: command not found` |

This is a reproducible dependency blocker, not a test failure attributed to the implementation and not evidence of a build pass.

## Deterministic pack checks

The following standard-library-only checker validates required and forbidden paths, entry types, canonical strict JSON snapshots, fixed manifest labels, and high-confidence credential patterns:

```bash
python3 sealed/validation/check_pack.py
```

The first attempt used a future-annotations import unsupported by the host interpreter. It exited `1` with:

```text
  File "sealed/validation/check_pack.py", line 4
    from __future__ import annotations
    ^
SyntaxError: future feature annotations is not defined
```

`python3 --version` then exited `0` and printed `Python 3.6.8`. The checker was adjusted to use Python 3.6-compatible syntax and rerun; the final observed result is recorded below.

Final observed exit status: `0`.

```text
PASS required files present: 23
PASS forbidden paths absent: 21
PASS all archived entries are regular files/directories: 79
PASS immutable JSON and GENERATED/PARTIAL labels match
PASS no credential-like patterns in generated files: 52
```

Both strict-JSON parse checks below also exited `0` with no standard output:

```bash
python3 -m json.tool MANIFEST.yaml >/dev/null
python3 -m json.tool PROVENANCE.json >/dev/null
```

## Not performed

- Go compilation or `gofmt` formatting
- unit, black-box, adversarial, or race-test execution
- fuzz execution or coverage measurement
- benchmark execution or profiler measurement
- upstream repository access or comparison
- independent review, transfer verification, or production hardening

The Go sources, tests, fuzz targets, and benchmark functions are reproducible inputs for later validators; their presence alone is not a validation result.
