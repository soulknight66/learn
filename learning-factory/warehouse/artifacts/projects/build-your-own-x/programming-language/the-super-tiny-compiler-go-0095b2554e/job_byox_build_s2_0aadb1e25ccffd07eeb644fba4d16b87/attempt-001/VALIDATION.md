# Validation record

Date: 2026-09-02 (America/Chicago)

## Go build and test attempt

Exact command, run from the repository root:

```bash
gofmt -w starter sealed/reference && (cd starter && go test ./...) && (cd sealed/reference && go test ./...)
```

Observed exit status: `127`. Observed stderr:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
/bin/bash: gofmt: command not found
```

Because `&&` stopped the command at the unavailable formatter, neither Go module
was compiled and no Go tests ran. No formatting mutation occurred.

Toolchain discovery command:

```bash
command -v go || true
command -v gofmt || true
ls -l /usr/local/go/bin/go /usr/local/go/bin/gofmt /usr/bin/go /usr/bin/gofmt /opt/go/bin/go /opt/go/bin/gofmt 2>/dev/null || true
```

Observed exit status: `0`; no Go or gofmt path was emitted. The same three
unmapped UID/GID wrapper diagnostics shown above preceded otherwise empty
output. Checks of `/usr/lib/go*/bin/go`, `/usr/lib/golang/bin/go`, and the exposed
`/arm/tools` Go conventions also emitted no executable candidate. No dependency
or toolchain was downloaded because network availability and third-party
artifacts were not assumed.

Result: build and behavioral-test validation is blocked by an unavailable Go
toolchain. Reference tests, public tests, fuzz campaigns, CLI runs, and
benchmarks were not executed. Their presence is not a passing result.

## Deterministic static audits

The first invocation of the audit scripts with the default Python failed at
import time because they initially used a future feature unavailable in Python
3.6.8. Observed error for both files was:

```text
SyntaxError: future feature annotations is not defined
```

The scripts were made Python 3.6-compatible and rerun. Exact final command:

```bash
python3 --version
python3 sealed/validation/audit.py
python3 sealed/validation/go_balance.py
```

Observed exit status: `0`. Observed substantive stdout:

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

The host wrapper again emitted the three unmapped UID/GID diagnostics before
stdout. `audit.py` requires all authoritative paths, rejects every forbidden
path and prefix, parses and pins both strict-JSON snapshots, enforces
`GENERATED` + `PARTIAL`, rejects symlinks/special files, checks common credential
shapes, and ensures exercise answers have a `sealed` path segment. The
factory-owned `.factory-workspace` marker is excluded from generated-file and
credential counts.

`go_balance.py` is only a lexical delimiter/string/comment sanity check. It is
not a Go parser, formatter, compiler, test runner, fuzzer, benchmark, security
review, or evidence of behavioral correctness.

## Status

The durable manifest remains `GENERATED` with validation labels exactly
`["GENERATED", "PARTIAL"]`. Independent validator-controlled execution is still
mandatory before any stronger label can be earned.
