# Validation record

Date: 2026-08-31 (America/Chicago)

Artifact labels remain `GENERATED` and `PARTIAL`. Independent validation is required. No `BUILDS`,
`TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` claim is made.

## Go toolchain and tests — blocked

Command group:

```text
go version
(cd public_tests && go test ./...)
(cd sealed/reference_tests && go test ./...)
```

Observed result:

```text
/bin/bash: go: command not found
go_version_exit=127
/bin/bash: line 3: go: command not found
public_tests_exit=127
/bin/bash: line 6: go: command not found
reference_tests_exit=127
```

The Go code was therefore not compiled, formatted by `gofmt`, vetted, or executed on this host.

## Shell and JSON syntax

Commands:

```text
sh -n environment/make-rootfs.sh
python3 -m json.tool MANIFEST.yaml >/dev/null
python3 -m json.tool PROVENANCE.json >/dev/null
```

Observed result: each exited 0 with no standard output. The JSON identity comparison is included in
the final structural check below.

## Integration rootfs — blocked by static C dependency

Command:

```text
./environment/make-rootfs.sh /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_v1_938f933c2b404d270fd3cb686636a9ce/attempt-001/environment/validation-rootfs
```

Observed result (exit 1):

```text
/usr/bin/ld: cannot find -lc
collect2: error: ld returned 1 exit status
static_rootfs_exit=1
```

The empty scratch directories were removed afterward. This host lacks the static libc archive, so no
usable chroot fixture was produced and namespace integration was not attempted.

## Dynamic probe source check

Commands:

```text
gcc -std=c11 -O2 -Wall -Wextra -Werror environment/probe.c -o environment/probe.validation
./environment/probe.validation --exit 0
unlink /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_v1_938f933c2b404d270fd3cb686636a9ce/attempt-001/environment/probe.validation
```

Observed result:

```text
hostname=vscode-login4.nahpc2.arm.com
pid=38
proc=mounted
dynamic_compile_exit=0 dynamic_run_exit=0 scratch_removed=yes
```

This validates the C source on the host only. A dynamically linked executable is not the promised
self-contained rootfs fixture.

## Final structural, boundary, and credential checks

Commands:

```text
python3 --version
python3 environment/verify-pack.py
```

Observed result (exit 0):

```text
Python 3.6.8
required_files=PASS (23)
forbidden_paths=PASS
regular_paths=PASS (62 files scanned)
learner_solution_paths=PASS
credential_scan=PASS (62 files scanned)
manifest_exact=PASS
provenance_exact=PASS
```

The verifier walks only authored artifact roots, not factory-owned control paths. Its immutable JSON
checks compare sorted compact representations, so whitespace is ignored but every JSON key, value,
array position, and absence of additional fields is bound. Credential scanning checks private-key
headers, common service-token prefixes, credential assignments, and URL userinfo; it is a useful
deterministic screen, not a general secret detector.
