# Independent validation record

Review date: 2026-08-31. `CANDIDATE/` was treated as immutable. Shell startup emitted unrelated UID/GID lookup warnings before command output; those warnings do not change the exit statuses below.

## Toolchain and executable checks

From `CANDIDATE/`:

```bash
go version
```

Exit `127`:

```text
/bin/bash: go: command not found
```

`command -v go`, `command -v gofmt`, `command -v gccgo`, and `command -v tinygo` returned no path. Checks of `/usr/local/go/bin/go`, `/usr/lib/golang/bin/go`, `/usr/bin/go`, and `/opt/go/bin/go` also found no executable. Python reported `Python 3.6.8`.

The following was attempted once from each listed module directory:

```bash
GOTOOLCHAIN=local go test ./...
```

| Module | Exit | Observed result |
| --- | ---: | --- |
| `starter/` | 127 | `/bin/bash: go: command not found` |
| `public_tests/` | 127 | `/bin/bash: go: command not found` |
| `sealed/reference/` | 127 | `/bin/bash: go: command not found` |
| `sealed/reference_tests/` | 127 | `/bin/bash: go: command not found` |

Consequently no Go source was compiled or formatted, and no unit, black-box, race, fuzz, or benchmark execution occurred. These are unavailable checks, not test failures and not pass evidence.

## Structural checker

From `CANDIDATE/`:

```bash
python3 sealed/validation/check_pack.py
```

Exit `0`:

```text
PASS required files present: 23
PASS forbidden paths absent: 21
PASS all archived entries are regular files/directories: 75
PASS immutable JSON and GENERATED/PARTIAL labels match
PASS no credential-like patterns in generated files: 52
```

This independently observes that the submitted script runs and accepts this tree; because the script is builder-authored, it is structural evidence only. Its `75`-entry result differs from the builder record's `79`.

An independent filesystem count/check produced:

```text
special_entries=0
files=52
directories_excluding_root=23
```

The command rejected anything other than a regular file or directory:

```bash
special=$(find CANDIDATE ! -type f ! -type d -print)
test -z "$special"
find CANDIDATE -type f -print | wc -l
find CANDIDATE -mindepth 1 -type d -print | wc -l
```

## JSON and provenance consistency

These both exited `0` with no parser diagnostics:

```bash
python3 -m json.tool CANDIDATE/MANIFEST.yaml >/dev/null
python3 -m json.tool CANDIDATE/PROVENANCE.json >/dev/null
```

An independent Python standard-library comparison observed:

```text
project_id_match=True
source_commit_match=True
manifest_hash_equals_snapshot_field=True
manifest_hash_equals_raw_provenance=False
manifest_hash_equals_canonical_provenance=False
raw_provenance_sha256=0ef563654487305f40e29ea6aade9bcce1477b623409b1038a95848b2f995b4d
canonical_provenance_sha256=c24359e1e81bcd65754e9fa978df2413709f99aabe63c0bb224fbcc378156217
```

Raw file hashes were:

```text
0ef563654487305f40e29ea6aade9bcce1477b623409b1038a95848b2f995b4d  CANDIDATE/PROVENANCE.json
ea4d7db5b05bd6edfd2a9e85831707e7f4d79299cafd59c49e1a93feb931626c  CANDIDATE/MANIFEST.yaml
```

## Static contract cross-checks

The following read-only search established the completion contradiction:

```bash
grep -n "empty program is legal\|Do not weaken\|Scan(\"\"\|CodeNotImplemented" \
  CANDIDATE/REQUIREMENTS.md CANDIDATE/AGENTS.md CANDIDATE/starter/types_test.go
```

Observed relevant lines:

```text
CANDIDATE/REQUIREMENTS.md:33:... An empty program is legal.
CANDIDATE/AGENTS.md:10:- Do not weaken, delete, or special-case tests.
CANDIDATE/starter/types_test.go:9:    _, err := Scan("")
CANDIDATE/starter/types_test.go:14:   if languageErr.Stage != StageScan || languageErr.Code != CodeNotImplemented {
```

Module/import inspection found that all sealed black-box, adversarial, fuzz, and benchmark tests import `example.com/pebble-reference`; only `public_tests/compiler_test.go` imports `example.com/pebble`. No external non-standard module requirement was found.

Readability checks observed:

```text
sealed_reference_readable=yes
sealed_answer_readable=yes
```

`MANIFEST.yaml` contains no sealed-path or learner-view declaration. This proves readability in the review archive, not what a separate factory-created learner process can access.

Manual static tracing of `sealed/reference/parser.go:191-200` found that its line-changing gap branch omits any next-column feasibility bound. The forged-coordinate defect in `REVIEW.md` was not executed because Go is unavailable.

## Candidate immutability

Before and after all inspection/checks, this command produced the same aggregate digest:

```bash
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

```text
3bcdff6a8457d190d2e95fa34ed7d554e2f67173d2de3516d05d670c97a3cc8c  -
```

No file under `CANDIDATE/` was edited.

## Limitations

- Go compilation, formatting, tests, race detection, fuzzing, benchmarks, and CLI execution are inconclusive because the toolchain is absent.
- Network and source-repository access are restricted, so upstream commit/license content and the no-copy assertion were not independently compared.
- No student-view construction or access-control validator was supplied, so sealed-material isolation is unverified.
- Builder-authored scripts and prose were not treated as evidence for any promoted validation label.
