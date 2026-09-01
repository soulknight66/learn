# Independent validation record

Date: 2026-08-31 (America/Chicago). Commands were run from the review workspace root. `CANDIDATE/` was treated as immutable; compilation and execution used a disposable copy. Each build/test command was bounded by `/usr/bin/timeout 30s`.

The wrapper emitted these unrelated warnings on each shell invocation; they are omitted from result summaries below:

```text
/usr/bin/id: cannot find name for user ID 532319
/usr/bin/id: cannot find name for group ID 500275
/usr/bin/id: cannot find name for user ID 532319
```

## Inventory and integrity

Commands:

```sh
find CANDIDATE -type f | wc -l
find CANDIDATE -type l -print
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Observed: 43 regular files, no symlinks, and aggregate digest:

```text
db9752b872350391a991657d906376d9a66b3cec4b7d65ef5762395afc7db167  -
```

The same digest was observed before and after all candidate checks. Scratch files were deleted with `find .review-scratch-independent -depth -delete`; the original candidate was never made writable.

## Environment

Command:

```sh
sh CANDIDATE/environment/check.sh
```

Exit `0`:

```text
Host requirements:
cc                           FOUND   cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make                         FOUND   GNU Make 4.2.1
Optional Raspberry Pi target tools:
aarch64-none-elf-gcc         MISSING
qemu-system-aarch64          MISSING
HOST_READY=yes
```

`clang`, `clang-tidy`, `cppcheck`, and `valgrind` were also unavailable.

## Metadata and static boundary checks

Commands and results:

```sh
cmp -s CANDIDATE/starter/include/pebble.h \
  CANDIDATE/sealed/reference/include/pebble.h
# exit 0

python3 -c 'import json; m=json.load(open("CANDIDATE/MANIFEST.yaml")); p=json.load(open("CANDIDATE/PROVENANCE.json")); assert m["project_id"] == p["project"]["project_id"]; assert m["source_id"] == p["source"]["source_id"] == p["project"]["source_id"]; assert m["source_commit"] == p["source"]["commit_hash"] == p["project"]["metadata"]["provenance"]["source_commit"]; assert m["provenance_sha256"] == p["snapshot_sha256"]; print("metadata_cross_links=PASS")'
# exit 0; metadata_cross_links=PASS

sha256sum CANDIDATE/PROVENANCE.json CANDIDATE/MANIFEST.yaml
# d960e0179a503ae026f4e37f80ba834ae989298f8e4b040c3cfd1166fa5aff57  CANDIDATE/PROVENANCE.json
# 42869204e8deae9db9ae3160e7ba90d68c81822dd2ff9a4ad26ff7f930e39c71  CANDIDATE/MANIFEST.yaml
```

The manifest's `provenance_sha256` is `d2775076...`, matching the provenance object's embedded `snapshot_sha256`; it is not the byte digest of the transferred `PROVENANCE.json`. Without the omitted builder `JOB.md`, only internal cross-link consistency—not exact equality to the factory input—was independently checkable.

A bounded independent grep for private-key headers and common AWS, OpenAI, GitHub, and bearer-token shapes returned exit `1` with no matches. The candidate-supplied scanner separately reported `credential_scan_files=43` and `credential_pattern_hits=[]`; neither result is a security certification.

Claim-language review found only `GENERATED` and `PARTIAL` in `validation_labels`, `productionized: false`, and `independent_validation: REQUIRED`. The prose explicitly says no fuzz, benchmark, Pi boot, independent production review, or transfer verification occurred.

## Isolated host builds and submitted tests

Setup:

```sh
mkdir .review-scratch-independent
cp -a CANDIDATE/. .review-scratch-independent/
chmod -R u+w .review-scratch-independent
```

The initial build attempt before the scratch-only `chmod` exited `2` because `cp -a` preserved read-only directory modes and `make` could not create `build/`. That setup failure was inconclusive and was corrected only in the disposable copy.

The following were then run with `.review-scratch-independent` as the working directory:

| Command | Exit | Observed result |
|---|---:|---|
| `make -C starter clean all` | 0 | Starter library compiled with strict C11 flags. |
| `make -C starter public` | 2 | Expected scaffold baseline: initialization passed; process, memory/fork, and filesystem cases failed at the same four assertions recorded by the builder. |
| `make -C sealed/reference clean all` | 0 | Reference library compiled with strict C11 flags. |
| `make -C sealed/reference_tests clean test` | 0 | All 14 submitted reference cases passed at O2. |
| `make -C sealed/reference_tests public` | 0 | All four public cases passed against the reference. |
| `make -C sealed/reference_tests clean test CFLAGS='-std=c11 -O0 -g -Wall -Wextra -Wpedantic -Werror'` | 0 | All 14 submitted reference cases passed at O0. |
| `make -C sealed/reference_tests clean sanitize` | 2 | Link failed: `/usr/lib64/libasan.so.5.0.0` and `/usr/lib64/libubsan.so.1.0.0` were unavailable. No sanitizer run occurred. |
| `make -C sealed/reference/pi3 clean all` | 2 | `aarch64-none-elf-gcc` was not found; no target object/image was produced. |
| `cc -std=c11 -Wall -Wextra -Wpedantic -Werror -ffreestanding -fsyntax-only sealed/reference/pi3/kernel.c` | 0 | Host front-end syntax only; not an AArch64 assembly, link, emulation, or boot result. |

The submitted test passes are observations, not independent validation labels.

## Reviewer-authored deterministic checks

A temporary independent C harness was compiled directly with the sealed reference under the same strict O2 flags. Before adding the focused failing assertion, it exited `0` and reported:

```text
PASS scheduler cursor/ready-set matrix (2048 cases)
PASS arithmetic boundaries, instance isolation, and rollback
PASS copy-on-write with exactly enough frame capacity
PASS all 256 open-flag values, name limits, modes, rollback
PASS checker index safety and nonmutation probes
all independent reviewer assertions passed
```

Coverage included every scheduler cursor and ready-set combination, `SIZE_MAX`/`UINT32_MAX` ranges, zero-length boundary behavior, tick/PID overflow rollback, a two-page COW write with exactly two free frames, every 8-bit open-flag value, maximum/overlong names, descriptor access modes, full-descriptor truncate rollback, and corrupt frame/file indices passed to the checker.

The harness was then augmented with this focused invariant probe:

```c
pebble_init(&kernel);
parent = pebble_process_create(&kernel);
pebble_vm_map(&kernel, parent, 0, PEBBLE_PAGE_READ);
child = pebble_process_fork(&kernel, parent); /* shared frame, refs == 2 */
kernel.processes[0].pages[0].flags |= PEBBLE_PAGE_WRITE;
result = pebble_check(&kernel, reason, sizeof(reason));
```

Compilation exited `0`. Execution exited `1` because the conformance assertion expected `PEBBLE_ERR_CORRUPT`. The actual observation was:

```text
OBSERVED shared-writable corruption: result=0 reason=''
FAIL: result == PEBBLE_ERR_CORRUPT
1 independent assertion(s) failed
```

This is a deterministic reference conformance failure. The augmented temporary harness had SHA-256 `c86921c62d2aaa39d7f949b754c33924f3834f74af886cd2b3b1d8abd2fc71c2` and was removed with the scratch products after its output was recorded.

## Supplied validation utilities

Command:

```sh
python3 CANDIDATE/sealed/validation/verify_pack.py
```

Exit `1` before any declared check:

```text
FileNotFoundError: [Errno 2] No such file or directory: '.../CANDIDATE/JOB.md'
```

`verify_pack.py` fixes its root at `CANDIDATE/` and unconditionally reads `JOB.md`, which is not submitted. Its recorded builder-workspace successes for required paths, forbidden paths, and exact metadata objects are therefore not reproducible here.

Command:

```sh
python3 CANDIDATE/sealed/validation/scan_credentials.py
```

Exit `0`:

```text
credential_scan_files=43
credential_pattern_hits=[]
```

## Progressive disclosure and learner usefulness

There are 22 regular files below `CANDIDATE/sealed/`. A search across the prose learner allowlist (`README.md`, `AGENTS.md`, `MANIFEST.yaml`, `REQUIREMENTS.md`, `CONCEPTS.md`, `DESIGN_QUESTIONS.md`, `starter/`, `public_tests/`, and `environment/`) for `sealed/`, sealed answers, reference implementations, or reference-test paths returned exit `1` with no matches.

This supports the static organization but does not verify transfer: no student-view tree, machine-readable export allowlist, or harness receipt was present. The linked upstream repository was not available, so the no-copy/originality statement and linked license could not be independently compared. The learner materials themselves are staged, detailed, and explicit about the host-model/Pi boundary; `README.md` contains the minor constant typo `PEB_ERR_NOT_IMPLEMENTED` instead of `PEBBLE_ERR_NOT_IMPLEMENTED`.

## Limitations

- No ASan/UBSan execution, alternate compiler/static analyzer, AArch64 build, QEMU run, hardware boot, fuzzing, benchmark, or stress run was available.
- No network/upstream snapshot or git executable was available; provenance originality and source history remain unverified.
- No actual learner export was supplied; sealed isolation after transfer is inconclusive.
- Pattern searches cannot prove the absence of all credentials or sensitive material.
