# Repair validation evidence

## Label boundary

This is worker-local evidence for repair generation 2. The authoritative manifest remains
`GENERATED` with only `GENERATED` and `PARTIAL`; `productionized` remains false and independent
validation remains required. Nothing below claims `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

The command launcher prepended `/usr/bin/id: cannot find name for user ID 532319` and analogous
account/group mapping warnings. Those ambient warnings were not emitted by pack programs and are
omitted from the observations below.

## Reviewed defect and repair

The generation-1 independent review found that `parse_number` returned its overflow classification
before examining the rest of a token. Valid nonnumeric names with overflowing decimal prefixes,
including `9223372036854775808x` and `-9223372036854775809x`, were therefore rejected as definition
names even though both are within the 31-byte name limit.

`sealed/reference/forth.S` now scans every post-sign byte to establish the complete decimal shape
before performing range-sensitive accumulation. An out-of-range all-digit token still receives the
integer-overflow classification, while a later nondigit makes the token nonnumeric. The two reviewer
reproducers are permanent cases in `sealed/reference_tests/test_reference.py`; sealed review and
test-development notes were updated to describe this exact boundary.

## Tool observations

Commands, run from the pack root:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/as --version | /usr/bin/sed -n '1p'
/usr/bin/ld.bfd --version | /usr/bin/sed -n '1p'
env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 --version
/usr/bin/uname -s -m
```

Observed, in order:

```text
Python 3.11.5
GNU assembler version 2.30-123.el8
GNU ld version 2.30-123.el8
qemu-x86_64 version 9.1.1
Copyright (c) 2003-2024 Fabrice Bellard and the QEMU Project developers
Linux x86_64
```

Pinned Python and configured QEMU were useful binaries invoked from their exact supplied roots.
QEMU required the configured GLib directory shown in `LD_LIBRARY_PATH`. No configured x86-64
binutils root was supplied, so the build used the exact regular host paths `/usr/bin/as` and
`/usr/bin/ld.bfd`. The configured Java and Arm toolchains were not applicable and were not used.

## Reconstruction-mode build attempt

Copying the checksum-bound prior pack also preserved its read-only mode bits. The first attempted
build command was:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py sealed/reference/forth.S -o sealed/reference/build/repro-a
```

It returned 1 before invoking the assembler because `pathlib.Path.mkdir` received
`PermissionError: [Errno 13] Permission denied` for `sealed/reference/build`. No executable was
created. Only the reconstructed top-level pack copy, never `PRIOR_BUILD/` or `PRIOR_REVIEW/`, was
then made owner-writable. The build was rerun successfully as recorded below. This failed workspace
preparation attempt is not treated as implementation evidence.

## Reproducible builds and ELF inspection

Commands:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py sealed/reference/forth.S -o sealed/reference/build/repro-a
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py sealed/reference/forth.S -o sealed/reference/build/repro-b
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/build.py starter/forth.S -o starter/build/cinder
/usr/bin/sha256sum sealed/reference/build/repro-a sealed/reference/build/repro-b starter/build/cinder
/usr/bin/cmp -s sealed/reference/build/repro-a sealed/reference/build/repro-b
/usr/bin/file sealed/reference/build/repro-a starter/build/cinder
/usr/bin/readelf -W -l sealed/reference/build/repro-a | /usr/bin/grep GNU_STACK
/usr/bin/readelf -W -s sealed/reference/build/repro-a | /usr/bin/grep '_start$'
/usr/bin/readelf -d sealed/reference/build/repro-a
```

All three builds returned 0. `cmp` returned 0. Observed hashes and relevant inspection output:

```text
b3e847dcfb3579a3a0029836ca3ea590076cad4399d714beae4ac38a95878092  sealed/reference/build/repro-a
b3e847dcfb3579a3a0029836ca3ea590076cad4399d714beae4ac38a95878092  sealed/reference/build/repro-b
72a0205dee22854aa726e476e3e61f01886d037a1aa324b2169034e1c3c017ff  starter/build/cinder
sealed/reference/build/repro-a: ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, not stripped
starter/build/cinder:           ELF 64-bit LSB executable, x86-64, version 1 (SYSV), statically linked, not stripped
GNU_STACK ... RW  0x10
278: 00000000004000e8    73 FUNC    GLOBAL DEFAULT    1 _start
There is no dynamic section in this file.
```

This additional command inspected the two reference images in memory:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'from pathlib import Path; a=Path("sealed/reference/build/repro-a").read_bytes(); b=Path("sealed/reference/build/repro-b").read_bytes(); print("byte_identical=%s workspace_path_embedded=%s random_scratch_prefix_embedded=%s" % (a == b, str(Path.cwd()).encode() in a, b".cinder-build-" in a))'
```

Observed:

```text
byte_identical=True workspace_path_embedded=False random_scratch_prefix_embedded=False
```

## Focused regression

The exact reviewer cases were run directly:

```text
/usr/bin/printf ': 9223372036854775808x 7 ; 9223372036854775808x . : -9223372036854775809x 8 ; -9223372036854775809x .\n' | /usr/bin/timeout --signal=KILL 5s sealed/reference/build/repro-a
```

The pipeline returned 0 and emitted exactly:

```text
7
8
```

The permanent focused test command was:

```text
env REFERENCE_BIN=sealed/reference/build/repro-a PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 sealed/reference_tests/test_reference.py ReferenceBoundaryTests.test_overflowing_decimal_prefix_can_be_a_word_name -v
```

Its named method reported `ok`; the summary was `Ran 1 test in 0.004s` and `OK`.

## Behavioral and tooling suites

Commands:

```text
env CINDER_BIN=sealed/reference/build/repro-a PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s public_tests -v
env REFERENCE_BIN=sealed/reference/build/repro-a PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s sealed/reference_tests -v
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m unittest discover -s environment -p 'test_*.py' -v
```

They ran concurrently and each returned 0. Every named method reported `ok`; none was skipped.
Observed summaries:

```text
Public:  Ran 10 tests in 0.019s -- OK
Sealed:  Ran 14 tests in 0.049s -- OK
Tooling: Ran  6 tests in 1.485s -- OK
```

The sealed count increased from 13 to 14 because of the focused two-case regression method.

## Native, QEMU, starter, and benchmark smoke checks

The native command was followed by three repetitions of the exact QEMU command:

```text
/usr/bin/printf ': square dup * ; 12 square .\n' | /usr/bin/timeout --signal=KILL 5s sealed/reference/build/repro-a
/usr/bin/printf ': square dup * ; 12 square .\n' | /usr/bin/timeout --signal=KILL 10s env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-x86_64 sealed/reference/build/repro-a
```

All four invocations returned 0; each wrote `144` followed by a newline. The longer QEMU bound was
chosen because the prior independent review saw intermittent cold-start timeouts at three seconds.
Three successful smoke repetitions demonstrate this configured emulator invocation but do not
establish transfer verification.

The starter command was:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import json, subprocess; p = subprocess.run(["starter/build/cinder"], input=b"", stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5, start_new_session=True); print(json.dumps({"returncode": p.returncode, "stderr": p.stderr.decode("ascii"), "stdout": p.stdout.decode("ascii")}))'
```

Observed:

```json
{"returncode": 2, "stderr": "error: interpreter not implemented\n", "stdout": ""}
```

This deliberate learner stub is the functional reason the artifact remains `PARTIAL`.

Benchmark-harness smoke command:

```text
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 benchmarks/run.py sealed/reference/build/repro-a --iterations 3 --terms 10 --timeout 5
```

It returned 0 and reported `minimum_ns: 1138655`, `median_ns: 1429091`, `maximum_ns: 1603413`,
`iterations: 3`, `terms_per_process: 10`, and `validation_label: UNVALIDATED_MEASUREMENT`. This is
only a harness smoke check and supports no performance or `BENCHMARKED` claim.

## Metadata and pre-cleanup audit

Commands:

```text
/usr/bin/sha256sum MANIFEST.yaml PROVENANCE.json
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
```

Observed hashes:

```text
c22f0d3691104fb2f03556eb89753678280c3ee082ee91b6daa9ecd39e6c8858  MANIFEST.yaml
a07dc4005276491142d98b5a1b764a7aa11342f525027ef38be2a9d01565ed87  PROVENANCE.json
```

The audit returned 0 before cleanup and emitted:

```json
{"credential_patterns": 4, "files_scanned": 37, "forbidden_absent": 21, "manifest_exact": true, "provenance_object_exact": true, "required_regular": 37, "special_entries_absent": true}
```

The audit requires all 37 checked-in files, checks all 21 forbidden paths, walks entry types without
following links, compares the exact authoritative manifest, binds the complete canonical provenance
object, and scans all pack files with four narrowly defined credential patterns. Build products are
excluded from the file scan and were present during this pre-cleanup invocation.

## Cleanup and final audit

After all executable-dependent checks, only these explicit scratch products were removed:

```text
/usr/bin/rm -- starter/build/cinder sealed/reference/build/repro-a sealed/reference/build/repro-b
/usr/bin/rmdir -- starter/build sealed/reference/build
```

Both commands returned 0. No executable, object, temporary fixture, symlink, bytecode cache, or
build directory is retained. A final post-record audit and an independent preservation check are
recorded after this validation file was completed.

Final commands:

```text
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit.py
env PYTHONDONTWRITEBYTECODE=1 /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import json; from pathlib import Path; r=Path.cwd(); p=r/"PRIOR_BUILD"; t=sorted(x.name for x in p.iterdir()); inv=lambda b:{(q.relative_to(b).as_posix(),q.is_dir()) for n in t for q in (([b/n]+list((b/n).rglob("*"))) if (b/n).is_dir() else [b/n])}; pi=inv(p); ci=inv(r); changed=sorted(n for n,d in pi&ci if not d and (p/n).read_bytes()!=(r/n).read_bytes()); expected=sorted(["VALIDATION.md","sealed/REVIEW.md","sealed/reference/forth.S","sealed/reference_tests/DEVELOPMENT_LOG.md","sealed/reference_tests/README.md","sealed/reference_tests/test_reference.py"]); py=sorted(r/n for n,d in ci if not d and n.endswith(".py")); [compile(x.read_bytes(),str(x.relative_to(r)),"exec") for x in py]; out={"artifact_inventory_exists":(r/"ARTIFACT_INVENTORY.sha256").exists(),"changed_files_match_expected":changed==expected,"compiled_python_files":len(py),"extra_entries":sorted(ci-pi),"missing_entries":sorted(pi-ci),"missing_prior_top_level_entries":sorted(n for n in t if not (r/n).exists()),"top_level_LICENSE_exists":(r/"LICENSE").exists()}; print(json.dumps(out,sort_keys=True))'
```

Both returned 0. Observed output:

```json
{"credential_patterns": 4, "files_scanned": 37, "forbidden_absent": 21, "manifest_exact": true, "provenance_object_exact": true, "required_regular": 37, "special_entries_absent": true}
{"artifact_inventory_exists": false, "changed_files_match_expected": true, "compiled_python_files": 6, "extra_entries": [], "missing_entries": [], "missing_prior_top_level_entries": [], "top_level_LICENSE_exists": false}
```

The independent comparison inventories every file and directory beneath the 17 prior top-level pack
entries. It found no additions or omissions and confirmed that the only content changes are this
validation record, the repaired parser, its regression and sealed documentation. It also compiled
all six Python files in memory without creating bytecode.

## Limitations

The immutable upstream catalog snapshot and linked resource were unavailable for independent
license, similarity, or clean-room authentication. Learner-view exclusion of `sealed/` is an
external control-plane property and was not transfer-verified here. No fuzzing, coverage run,
validated benchmark, production review, or broader platform matrix was performed. Fresh independent
validation remains mandatory.
