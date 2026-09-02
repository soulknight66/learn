# Independent validation record

Date: 2026-09-02 (America/Chicago)

Scope: read-only review of `CANDIDATE/`. The three review artifacts were written
beside it. Every command emitted the host's three unmapped UID/GID diagnostics;
those wrapper messages are omitted below unless material to the result.

## Reviewed snapshot and structure

From the workspace root:

```bash
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Exit 0:

```text
afdda3d1758070f3b7bf71243fb175f25d2402842d4125342d098aba9ff4d581  -
```

This is a reviewer-computed aggregate of sorted per-file checksum lines, not a
factory provenance identifier.

```bash
find CANDIDATE -type f | wc -l
find CANDIDATE -type l -print
find CANDIDATE -type f -printf '%m\n' | sort -u
find CANDIDATE -type d -printf '%m\n' | sort -u
```

Observed: 67 regular files; the symlink query printed nothing; all files reported
mode `444`; directories reported only `555` and `2555`. The candidate was not
modified.

An inventory made once while pruning every path below a segment named `sealed`
contained 33 learner-facing files and no `ANSWER.md`, reference implementation,
or reference-test file. This establishes placement only, not the behavior of the
factory's student-view generator.

## Structural scripts

Run from `CANDIDATE/`:

```bash
python3 --version
python3 sealed/validation/audit.py
python3 sealed/validation/go_balance.py
```

All exited 0. Substantive output:

```text
Python 3.6.8
required-files: OK
forbidden-paths: OK
strict-json-snapshots: OK
file-types: OK
credential-patterns: OK
exercise-answer-isolation: OK
generated-file-count: 67
go-lexical-balance: OK
go-source-files: 30
```

The two scripts are candidate-authored. Their observed result corroborates file
structure only; it does not prove Go parsing or behavior.

## Independent manifest and provenance checks

Duplicate-key-rejecting `json.loads(..., object_pairs_hook=...)` checks parsed
both snapshots successfully. A separate canonicalization and identifier check
reported:

```text
manifest-canonical 4e6c88e18008226e3f64c0e2c366ec6aafb2b859f2a5557054fa3feaed6c1c59
provenance-canonical d75f0974ef139507894b6414cedf2feb9bcd216eb787792a7f0c3229c01b15df
manifest.provenance_sha256 d170405a21f267cd6f7fadc506a8fc9ed456b8ed2abc74ac445057c8e9ed9626
provenance.snapshot_sha256 d170405a21f267cd6f7fadc506a8fc9ed456b8ed2abc74ac445057c8e9ed9626
project-id-match True
source-id-match True
commit-match True
```

The canonical digests equal the pins in `sealed/validation/audit.py`.
`MANIFEST.yaml` reports `GENERATED`, labels `["GENERATED", "PARTIAL"]`, required
independent validation, and `productionized: false`.

The claim scan command was:

```bash
grep -RInE '\b(BUILDS|TESTED|FUZZED|BENCHMARKED|REVIEWED|TRANSFER_VERIFIED|PRODUCTIONIZED)\b' CANDIDATE
```

Exit 0 with one match: `benchmarks/README.md:14`, a warning not to infer the
`BENCHMARKED` label. No affirmative stronger-label claim was found.

Static module inspection found Go 1.20 declarations, only local `replace`
directives, and imports limited to the Go standard library plus
`example.com/prefixforge`. Scaffold/reference exported bytecode declarations were
identical; reference-only additions did not remove scaffold fields or functions.

## Go toolchain and bounded test attempts

```bash
command -v go
command -v gofmt
command -v gccgo
command -v tinygo
command -v gopls
go version
```

Each `command -v` exited 1 with no path. `go version` exited 127 with:

```text
/bin/bash: go: command not found
```

The following exact command was attempted independently in each listed working
directory:

```bash
timeout 30s go test ./...
```

| Working directory | Exit | Observed result |
| --- | ---: | --- |
| `CANDIDATE/starter` | 127 | `timeout: failed to run command 'go': No such file or directory` |
| `CANDIDATE/public_tests` | 127 | same |
| `CANDIDATE/sealed/reference` | 127 | same |
| `CANDIDATE/sealed/reference_tests` | 127 | same |
| `CANDIDATE/debugging/jump_patch` | 127 | same |
| `CANDIDATE/debugging/lexer_position` | 127 | same |

No package was loaded and no Go test executed. No formatter, CLI run, fuzz
campaign, benchmark, race test, or cross-platform test ran.

## Static review performed

All 67 files were read. Review included contract/reference consistency, token and
span rules, nesting and source limits, type rules, checked arithmetic, lazy
branches, compiler stack accounting, bytecode control-flow verification, VM step
and stack limits, writer errors, CLI dispatch, public/reference test intent,
exercise answer placement, validation-label language, and provenance/license
boundaries.

Static inspection found no blocking implementation contradiction. It did find an
undefined `string-character` grammar term, no end-to-end CLI tests, and incomplete
realization of several suggested adversarial cases. These are documented in
`REVIEW.md`; static inspection is not substituted for execution evidence.

## Limitations and label decision

- Go buildability and behavior are inconclusive because the required toolchain is
  unavailable.
- Candidate-authored scripts and test source do not prove execution labels.
- Network/upstream source material was unavailable, so external provenance and
  no-copy claims were not independently compared.
- The actual learner-view export was unavailable; only sealed path placement was
  checked.

No evidence from this review establishes `BUILDS`, `TESTED`, `FUZZED`,
`BENCHMARKED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`. The `PASS` in
`EVALUATION.json` is advisory for review quality and honest partial labeling only;
it does not itself publish `REVIEWED`.
