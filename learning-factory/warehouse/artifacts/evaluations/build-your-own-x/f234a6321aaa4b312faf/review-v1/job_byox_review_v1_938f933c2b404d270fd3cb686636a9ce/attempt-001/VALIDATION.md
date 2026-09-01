# Independent validation record

Date: 2026-08-31 (America/Chicago)

Scope: read-only inspection and safe, bounded checks of `CANDIDATE/`. No candidate file was edited.
Commands were run from the review workspace unless a module directory is shown. Harness messages
about the numeric user/group lacking a local name were environmental noise and are omitted below.

## Candidate immutability and inventory

Commands:

```text
find CANDIDATE -printf '%y %m %s %p\n' | sort
find CANDIDATE -type l -ls
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Observed:

```text
62 regular files
0 symbolic or special paths
regular-file modes: 0444, except environment/make-rootfs.sh: 0555
aggregate_before=6bf7ee040a01cc25626bcfdfb770530122aeac983a11b5c6b1934818d9ac764d
aggregate_after=6bf7ee040a01cc25626bcfdfb770530122aeac983a11b5c6b1934818d9ac764d
```

The aggregate hashes the sorted `sha256sum` records (including relative filenames), not merely file
contents concatenated together.

## Available toolchains

Commands:

```text
command -v go
go version
command -v gccgo
command -v tinygo
command -v gcc
gcc --version
command -v python3
python3 --version
command -v git
command -v shellcheck
uname -srm
```

Observed:

```text
go: unavailable; go version exited 127
gccgo: unavailable
tinygo: unavailable
gcc: /usr/bin/gcc
gcc (GCC) 8.5.0 20210514
python3: /usr/bin/python3
Python 3.6.8
git: unavailable
shellcheck: unavailable
Linux 4.18.0-553.el8_10.x86_64 x86_64
```

A bounded search below `/arm/tools` also found no `go` or `gofmt` executable.

## Go builds, tests, and benchmarks — blocked

Each command was wrapped in `timeout 30s` and run from the indicated module:

```text
(cd CANDIDATE/starter && go build ./cmd/tinycontainer)
(cd CANDIDATE/public_tests && go test ./...)
(cd CANDIDATE/sealed/reference && go build ./cmd/tinycontainer)
(cd CANDIDATE/sealed/reference_tests && go test ./...)
(cd CANDIDATE/adversarial && go test ./...)
(cd CANDIDATE/debugging/exercise_01 && go test ./...)
(cd CANDIDATE/debugging/exercise_02 && go test ./...)
(cd CANDIDATE/benchmarks && go test -run '^$' -bench . -benchmem)
```

Observed for all eight commands:

```text
timeout: failed to run command 'go': No such file or directory
exit=127
```

Consequently, no `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, formatting, vetting, race, or
cross-platform conclusion is supported by this review.

## JSON identity and structural verifier

Commands:

```text
python3 -m json.tool CANDIDATE/MANIFEST.yaml >/dev/null
python3 -m json.tool CANDIDATE/PROVENANCE.json >/dev/null
python3 CANDIDATE/environment/verify-pack.py
python3 -c 'import ast, pathlib; ast.parse(pathlib.Path("CANDIDATE/environment/verify-pack.py").read_text(encoding="utf-8")); print("verify_pack_ast=PASS")'
```

Observed:

```text
manifest_json_exit=0
provenance_json_exit=0
required_files=PASS (23)
forbidden_paths=PASS
regular_paths=PASS (62 files scanned)
learner_solution_paths=PASS
credential_scan=PASS (62 files scanned)
manifest_exact=PASS
provenance_exact=PASS
verify_pack_ast=PASS
```

An independent JSON comparison observed:

```text
project_id_consistent=true
source_id_consistent=true
source_commit_consistent=true
manifest_provenance_pointer_consistent=true
status_and_labels_consistent=true
manifest_canonical_sha256=a6c0ad16ef85530b00a79e13f644d0275ff03a10d9efd89a1ff644fbf0090ab8
provenance_canonical_sha256=4f9ec0833062cad5a7546998cd50978af81b8f68c584a057bd75d59920a9a8c0
```

The submitted verifier was inspected before execution. Running builder-authored code establishes
only its observed mechanics. In particular, it checks path layout rather than a separately exported
student view, and hard-coded digests establish internal identity rather than upstream truth.

## Shell helper and C probe

Commands:

```text
sh -n CANDIDATE/environment/make-rootfs.sh
./CANDIDATE/environment/make-rootfs.sh relative-rootfs
./CANDIDATE/environment/make-rootfs.sh /
gcc -std=c11 -O2 -Wall -Wextra -Werror CANDIDATE/environment/probe.c -o .review-scratch/probe.dynamic
CHECK=independent-review timeout 10s .review-scratch/probe.dynamic --exit 0
timeout 10s .review-scratch/probe.dynamic --exit 17
timeout 20s ./CANDIDATE/environment/make-rootfs.sh /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_review_v1_938f933c2b404d270fd3cb686636a9ce/attempt-001/.review-scratch/static-rootfs
```

Observed:

```text
shell_syntax_exit=0
rootfs path must be absolute
relative_target_exit=64
refusing to use host root
host_root_exit=64
dynamic_compile_exit=0
hostname=vscode-login4.nahpc2.arm.com
pid=40
proc=mounted
CHECK=independent-review
dynamic_exit_0=0
hostname=vscode-login4.nahpc2.arm.com
pid=42
proc=mounted
dynamic_exit_17=17
/usr/bin/ld: cannot find -lc
collect2: error: ld returned 1 exit status
static_fixture_exit=1
```

The failed static build left only `static-rootfs/bin/` and `static-rootfs/proc/`; the dynamic binary
and all reviewer-created scratch paths were explicitly removed. A dynamic host executable is not a
self-contained chroot fixture, so namespace integration was not attempted.

## Claim, boundary, and narrow credential checks

Commands:

```text
grep -RInE --exclude='*.go' --exclude='probe.c' 'BUILDS|TESTED|FUZZED|BENCHMARKED|REVIEWED|TRANSFER_VERIFIED|PRODUCTIONIZED|productionized|independent validation|PASS' CANDIDATE
grep -RIlE --exclude='VALIDATION.md' --exclude='verify-pack.py' -e '-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----|(AKIA|ASIA)[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{30,}|https?://[^/[:space:]:@]+:[^/[:space:]@]+@' CANDIDATE
find CANDIDATE -path '*/sealed/*' -type f | wc -l
```

Observed:

```text
All validation-label mentions deny promotion claims or describe narrowly scoped verifier output.
narrow_credential_scan_exit=1 (no match)
solution-bearing sealed-path files=25
```

The manifest and prose are honest about partial status. The credential scan is intentionally narrow
and cannot establish the absence of every possible secret. The 25 files are expected to be visible
to an independent reviewer; no actual student projection was available to prove their exclusion.

## Static correctness review

The reviewer manually traced R1-R20 through the reference and its tests. Two concrete mismatches were
found without executing privileged code:

1. `cmd/tinycontainer/main.go` enters child mode solely from the first argv marker. The child accepts
   the literal descriptor number 3 without checking an inherited channel or namespace state, then
   performs mount, hostname, chroot, and proc setup. Direct internal-mode invocation can therefore
   bypass the parent's fresh clone flags.
2. `parseConfigArgs` uses standard `flag.FlagSet.Parse` and never records whether `--` appeared.
   Standard flag parsing stops at the first positional argument, so R7's mandatory command separator
   is not enforced. Submitted tests cover only the positive, separator-present form.

No privileged runtime was executed to demonstrate the first issue; its impact follows directly from
the dispatch and syscall order. Additional test-coverage and licensing findings are detailed in
`REVIEW.md`.

## Limitations

- Go compilation, formatting, vetting, unit tests, fuzzing, benchmarks, and runtime integration are
  inconclusive because the Go toolchain is unavailable.
- Static linking is unavailable, and namespace policy was deliberately not probed without a usable
  disposable fixture.
- Git/source snapshots and network access were unavailable, so source commit/tree, CC0 evidence,
  linked-resource non-copying, and similarity assertions were not externally reproduced.
- Shellcheck was unavailable; `sh -n` checks syntax only.
- No harness-created learner view or transfer report was supplied, so progressive-disclosure
  enforcement remains unverified.
