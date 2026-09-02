# Independent validation record

Date: 2026-09-02 (America/Chicago)

Scope: read-only review of `CANDIDATE/`. All compiling and execution occurred in the temporary reviewer clone `.review-scratch.aoCDWh`, which was made writable and removed after testing. No candidate manifest or submitted file was edited. Results below are observations, not promotions to `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`.

The shell emitted harmless identity warnings (`/usr/bin/id: cannot find name for user ID 532319`) before commands; they did not change exit status or test output.

## Tool identities

Each relevant configured tool was invoked by exact path:

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc --version
arm-none-eabi-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-readelf --version
GNU readelf (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-nm --version
GNU nm (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203

$ /usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm --version
QEMU emulator version 9.1.1

$ /usr/bin/make --version
GNU Make 4.2.1

$ /usr/bin/timeout --version
timeout (GNU coreutils) 8.30
```

Java, AArch64, Node, Go, NASM, Flex, and Bison were irrelevant and were not invoked. `rg` and `git` were unavailable; `find`, `grep`, direct reads, and configured Python were used.

## Submission integrity and structure

```sh
find CANDIDATE -type f | wc -l
find CANDIDATE -type d | wc -l
find CANDIDATE -type l -o -type p -o -type s -o -type b -o -type c
```

Observed: 101 regular files, 36 directories including `CANDIDATE`, and no listed symlink or special object. An independent Python scan found zero configured credential-pattern matches and zero hard-link groups. No setuid/setgid regular file was found. Starter and reference copies of all six public headers compared byte-identical.

The manifest and provenance parsed as JSON. Observed labels were exactly `GENERATED,PARTIAL`; project/source/commit identifiers agreed; `MANIFEST.provenance_sha256` equaled `PROVENANCE.snapshot_sha256`; the provenance file itself hashed to:

```text
6a0410262aad87532cd91b268236eb2c8f52cb7ebfef93dbdba15f3a553f440d  CANDIDATE/PROVENANCE.json
```

An independent comparison against the constant embedded in the submitted audit used:

```sh
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c \
  'import json,runpy; n=runpy.run_path("CANDIDATE/sealed/pack_audit.py"); a=json.load(open("CANDIDATE/MANIFEST.yaml",encoding="utf-8")); print(a==n["EXPECTED_MANIFEST"])'
```

Observed `True`, exit 0. This is why the later pack-audit manifest-mismatch message is classified as spurious.

Before testing and again afterward:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Observed both times:

```text
db46cb9476c1a7960f53a1df35014ad19293f9d360737a40541edb052e2bded9  -
```

## Writable review clone

```sh
mktemp -d -p . .review-scratch.XXXXXX
/bin/cp -a CANDIDATE/. .review-scratch.aoCDWh/
```

The immutable submission uses read-only modes (`CANDIDATE` mode 2555, regular files generally 0444, directories 0555). Because `cp -a` preserved those modes, the first cloned `make clean test`/clean-build attempts exited 2 with `Permission denied` while creating or removing `build/`; they did not exercise the code. The reviewer then ran:

```sh
/bin/chmod -R u+w .review-scratch.aoCDWh
```

Only the clone was changed. All results reported below are the subsequent successful reruns.

## Host validation

Common compiler and runtime settings:

```text
CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64
ASAN_OPTIONS=detect_leaks=0
```

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C sealed/reference_tests clean test \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'

/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C adversarial clean test \
  PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'

/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C public_tests clean test KERNEL_SRC=../sealed/reference \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed:

```text
reference_tests: PASS (407 checks)                         exit 0
adversarial_vectors: PASS (12 vectors)                     exit 0
public_tests against ../sealed/reference: PASS             exit 0
```

The same sanitized public command with `KERNEL_SRC=../starter` printed `public_tests: 37 check(s) failed` and `make` exited 2. This exactly reproduced the documented, intentionally incomplete baseline.

A temporary reviewer-authored C harness was compiled directly against the reference scheduler, VM, and RAMFS sources with C11, `-Wall -Wextra -Werror -pedantic`, ASan, and UBSan. It added deterministic checks for multi-wrap rotation, block/unblock/exit/reap transitions, corrupt enum/current state rejection without mutation, exact 32-bit frame boundaries, retain overflow, permission combinations, unchanged translation output, full mapping capacity, maximum-length names, holes, integer wrap, zero-length I/O, and full-record unlink scrubbing:

```text
reviewer_extra: PASS (86 checks)                            exit 0
```

The temporary harness and executable were deleted with the review clone; they are independent review observations, not candidate artifacts.

## Learner-view isolation

```sh
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s environment -p 'test_*.py' -v
```

Observed: all five tests `ok`, `Ran 5 tests`, `OK`, exit 0.

Source-input audit:

```sh
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/audit_student_view.py --source-pack .
```

Observed exit 0:

```json
{"directories": 12, "entries": 55, "inventory_sha256": "d1879d8df860f1b346cd3ddfb9d0bdfe8c74bc9e2d52447995b1bdfc858abdfc", "mode": "allowlisted-source", "regular_files": 43, "status": "PASS"}
```

The reviewer separately copied exactly the six allowlisted root files and three allowlisted root directories from immutable `CANDIDATE/` into `learner-view/`, then ran:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/audit_student_view.py \
  --policy environment/student_view_policy.json --view learner-view --list
```

Observed `status=PASS`, `mode=materialized-view`, 55 entries, 43 files, 12 directories, the same inventory digest, and exit 0. The full inventory contained no sealed/reference implementation; searches for reference implementation symbols in allowlisted material found none.

Negative integration checks observed:

```text
extra root file: student_view_audit: FAIL: ... extra=['EXTRA']          exit 1
in-tree symlink: student_view_audit: FAIL: symbolic link is forbidden  exit 1
```

The strict inventory also demonstrated the review finding: `LICENSE_BOUNDARY.md`, `debugging/`, and `review_exercises/` are absent from the defined learner view.

## Cross-build and ELF inspection

```sh
/usr/bin/timeout 45s /usr/bin/make -C sealed/reference clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-

/usr/bin/timeout 45s /usr/bin/make -C starter clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

Both exited 0 with no warning. Fresh hashes and sizes were:

```text
43dc67083d95cc6316da74f1811bacdd0da4d95c19cbc6244012d8fc70696d73  sealed/reference/build/kernel.elf  (12516 bytes)
b0a152b88f7f284512f82b46453ba20b6d44146841ffe240ea13c49b1b799021  sealed/reference/build/kernel.bin  (5448 bytes)
fb01da0cf9457b8dc372fa52a8abcdf8d9e0e7406cf3c2105c69512591ca8ee4  starter/build/kernel.elf           (5076 bytes)
a5e6978210f45b0fc27c1604276123099f26f15e2857d30a34a7d6a0b50d2f74  starter/build/kernel.bin           (120 bytes)
```

All values exactly match the candidate record. Arm `readelf -h -l` observed ELF32, little-endian Arm EABI5, entry `0x10000`, one RX load segment, one RW load segment, and an RW/non-executable GNU stack. This command emitted no symbols and exited 0:

```sh
/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-nm \
  -u sealed/reference/build/kernel.elf
```

## Bounded QEMU execution

```sh
/usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /usr/bin/timeout 10s \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  -M versatilepb -cpu arm926 -m 128M -nographic -monitor none \
  -semihosting-config enable=on,target=native \
  -kernel sealed/reference/build/kernel.elf
```

Observed exit 0 and ordered UART output:

```text
LF-KERNEL boot
mmu: on
vm: ok
ramfs: ok
tasks: ABABAB
PASS reference
```

Replacing the kernel with `starter/build/kernel.elf` and using a two-second bound emitted no kernel marker, printed QEMU's signal-15 termination notice, and exited 124. This is consistent with the visible UART/MMU stubs and is not success evidence.

## Other bounded checks

Both isolated exercise C files passed a single GCC 15.2.0 `-fsyntax-only` invocation with `-std=c11 -Wall -Wextra -Werror -pedantic`, exit 0. The diagnostic benchmark compiled with the same GCC and exit 0; it was not run or treated as benchmark evidence.

## Unreproduced pack audit and remaining limitations

Exact submitted command:

```sh
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/sealed/pack_audit.py --pack-root CANDIDATE
```

Observed exit 1:

```text
pack_audit: FAIL: metadata parse failure: [Errno 2] No such file or directory: 'CANDIDATE/PRIOR_BUILD/PROVENANCE.json'; manifest does not equal the authoritative object; unexpected omitted prior files: []
```

`PRIOR_BUILD/` is not part of the submitted material, so the builder's prior-path preservation counts, prior aggregate hash, and pack-audit PASS remain inconclusive. Separate current-pack inventory, metadata, credential, learner-isolation, and hash checks are recorded above; they do not reconstruct the absent baseline.

The immutable catalog snapshot and upstream repository were unavailable, and network access was not used. The no-copy/origin assertion therefore could not be independently compared with upstream. No physical board, transfer environment, fuzzer, repeated timing study, formal proof, security audit, or production workload was available or attempted.

After validation, the exact temporary review clone was made writable and removed with `/bin/rm -r -- .review-scratch.aoCDWh`; verification showed it absent. Only `EVALUATION.json`, `REVIEW.md`, and this file were added outside immutable `CANDIDATE/`.
