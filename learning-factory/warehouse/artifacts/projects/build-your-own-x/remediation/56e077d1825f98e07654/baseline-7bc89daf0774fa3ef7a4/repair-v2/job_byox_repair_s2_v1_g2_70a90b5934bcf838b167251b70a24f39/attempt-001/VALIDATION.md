# Validation evidence

Date: 2026-09-02 (America/Chicago)

Disposition: fresh repair-generation-2 evidence only. `MANIFEST.yaml` remains
exactly `GENERATED` + `PARTIAL`, requires independent validation, and keeps
`productionized` false. These observations do not assign `BUILDS`, `TESTED`,
`FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`;
only a worker-harness validator may promote labels.

No network access, upstream checkout, physical board, learner workspace, or
actual learner-view materialization was used. The learner-view unit test creates
and removes only a synthetic miniature filesystem fixture.

## Repair scope

The archived independent review requested four publication/harness repairs:

1. Both disclosure policies now include `LICENSE_BOUNDARY.md`.
2. `adversarial/run_vectors.py` starts a new session, kills its process group on
   timeout, waits for the direct child, drains and truncates captured output,
   and kills lingering same-group descendants after normal direct-child exit.
3. `sealed/pack_audit.py --pack-root .` is self-contained. Historical
   preservation is a separate opt-in mode requiring both `--prior-root` and the
   sealed `--prior-record`; missing prior data cannot invalidate a successfully
   parsed current manifest.
4. Initial and post-attempt disclosure have separate JSON policies. The latter
   selects exercise prose and fixtures exactly, never their sibling `sealed/`
   directories. The materializer audits before copy, copies without following
   file symlinks, strictly re-audits the staged destination, compares complete
   inventories, and publishes only by final rename.

## Tool identities

Every relevant configured binary was invoked by exact path:

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc --version
arm-none-eabi-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-readelf --version
GNU readelf (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-objcopy --version
GNU objcopy (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203

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

Java, AArch64, Node, Go, NASM, Flex, and Bison were irrelevant and were not
invoked. `rg` was unavailable; `find`, `sed`, and configured Python were used.
The shell emitted identity lookup warnings for numeric sandbox user/group IDs;
the recorded commands' exit statuses and program output were unaffected.

## Publication policies and materializer

Eight deterministic policy/materializer tests were run:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s environment -p 'test_*.py' -v
```

Observed: all eight tests `ok`, `Ran 8 tests`, `OK`, exit 0. Coverage includes
license presence in the initial policy, the exact post-attempt file list,
case-insensitive forbidden components, strict top-level matching, nonregular
entry rejection, nested-answer rejection, stable inventory hashing, and a
synthetic end-to-end materialization that proves an unselected `sealed/ANSWER.md`
is absent and that source and strict destination inventories match.

After all host-linked scratch products were cleaned, both source selections were
audited without creating a learner view:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/audit_student_view.py \
  --policy environment/student_view_policy.json --source-pack .
```

Observed exit 0:

```json
{"directories": 12, "entries": 58, "inventory_sha256": "c6f8db62ce0b4ef74cad2045fb59d42c7fdb76379a5cb20e7e14923b94e19f57", "mode": "allowlisted-source", "regular_files": 46, "stage": "initial", "status": "PASS"}
```

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/audit_student_view.py \
  --policy environment/post_attempt_view_policy.json --source-pack .
```

Observed exit 0:

```json
{"directories": 16, "entries": 68, "inventory_sha256": "2745e745a78d8953aff4a481e2830e0a42946b90127a5b394366df83bc96e9bb", "mode": "allowlisted-source", "regular_files": 52, "stage": "post-attempt-exercises", "status": "PASS"}
```

These source-input passes validate the two selections but are not publication
evidence. An independent orchestrator must materialize and retain strict
`--view --list` evidence for each stage it publishes.

## Process-group containment and adversarial vectors

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 PYTHONDONTWRITEBYTECODE=1 \
  /usr/bin/make -C adversarial clean test \
  PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed exit 0. The bounded-runner suite reported three tests `ok`, `Ran 3
tests`, `OK`; these check successful capture, 1,024-byte truncation of both
streams, and timeout of a helper that first proves its descendant started. The
test waited past the descendant's delayed marker time and observed that the
marker remained absent. The sanitized C execution then reported:

```text
adversarial_vectors: PASS (12 vectors)
```

This is deterministic vector coverage, not a fuzz campaign or a `FUZZED` label.

## Pack audit separation, structure, and prior binding

Four unit tests cover canonical content digesting, per-document JSON failure
isolation, exact prior-record metadata, and submission-local operation:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest sealed/test_pack_audit.py -v
```

Observed: all four tests `ok`, `Ran 4 tests`, `OK`, exit 0.

A preliminary concurrent run of this exact command overlapped the environment
materializer's synthetic temporary fixture. The strict current-pack test
correctly rejected transient top-level `tmpx_diiu_f`, so that concurrent command
exited 1. The environment test removed its owned fixture; the isolated rerun
above then exited 0. No exception was added to the pack allowlist.

The final submission-local command was:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/pack_audit.py --pack-root .
```

Observed exit 0:

```text
pack_audit: PASS
required_count=23 missing=0
forbidden_count=21 present=0
pack_regular_files=107 pack_directories=35
symlink_count=0 special_count=0 hard_link_groups=0
learner_forbidden_component_count=0
credential_scan=no_matches
unexpected_top_level_count=0
manifest_exactness=PASS
provenance_consistency=PASS
historical_comparison=SKIPPED(no prior input)
```

Historical preservation was separately exercised with explicit external and
record inputs:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/pack_audit.py --pack-root . \
  --prior-root PRIOR_BUILD --prior-record sealed/prior_baseline.json
```

Observed exit 0:

```text
pack_audit: PASS
required_count=23 missing=0
forbidden_count=21 present=0
pack_regular_files=107 pack_directories=35
symlink_count=0 special_count=0 hard_link_groups=0
learner_forbidden_component_count=0
credential_scan=no_matches
unexpected_top_level_count=0
manifest_exactness=PASS
provenance_consistency=PASS
historical_comparison=PERFORMED
prior_content_sha256=44390f7023c56dfbe64e02542f89581607e19b84ec9d39621029b13fe7a7be54
prior_artifact_checksum_recorded=90e76bbf81bf98e575baa0568818e39c78f732dcd62a7dfd7cb9c8e2f7c6cf20
prior_regular_files=101
prior_files_omitted=0
prior_directories=35
prior_directories_omitted=0
repair_files_added=6
prior_files_modified=13
```

`sealed/prior_baseline.json` records factory artifact checksum
`90e76bbf81bf98e575baa0568818e39c78f732dcd62a7dfd7cb9c8e2f7c6cf20`
under its supplied `tree-sha256-v2` name and independently binds the staged
tree's paths, object types, sizes, and file SHA-256 values with the documented
`canonical-path-content-sha256-v1` digest. The audit does not claim to
reimplement the factory checksum algorithm.

## Portable reference and public tests

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C sealed/reference_tests clean test \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `reference_tests: PASS (407 checks)`, exit 0, with AddressSanitizer and
UndefinedBehaviorSanitizer enabled.

The same compiler/sanitizer environment ran the public suite against the
reference and then the starter:

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C public_tests clean test \
  KERNEL_SRC=../sealed/reference \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `public_tests: PASS`, exit 0.

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C public_tests clean test KERNEL_SRC=../starter \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `public_tests: 37 check(s) failed`; make exited 2. This is the expected,
intentionally incomplete staged baseline, not passing starter evidence.

## ARM clean builds and ELF inspection

```sh
/usr/bin/timeout 45s /usr/bin/make -C sealed/reference clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-

/usr/bin/timeout 45s /usr/bin/make -C starter clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

Both commands exited 0 with no compiler/linker warning. Fresh retained artifact
observations were:

```text
43dc67083d95cc6316da74f1811bacdd0da4d95c19cbc6244012d8fc70696d73  sealed/reference/build/kernel.elf
b0a152b88f7f284512f82b46453ba20b6d44146841ffe240ea13c49b1b799021  sealed/reference/build/kernel.bin
fb01da0cf9457b8dc372fa52a8abcdf8d9e0e7406cf3c2105c69512591ca8ee4  starter/build/kernel.elf
a5e6978210f45b0fc27c1604276123099f26f15e2857d30a34a7d6a0b50d2f74  starter/build/kernel.bin
sealed/reference/build/kernel.elf  12516 bytes
sealed/reference/build/kernel.bin   5448 bytes
starter/build/kernel.elf            5076 bytes
starter/build/kernel.bin             120 bytes
```

```sh
/usr/bin/timeout 15s \
  /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-readelf \
  -h -l sealed/reference/build/kernel.elf
```

Observed exit 0: ELF32, little-endian ARM EABI5, entry `0x10000`, one RX load
segment, one RW load segment, and an RW/non-executable GNU stack.

```sh
/usr/bin/timeout 15s \
  /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-nm \
  -u sealed/reference/build/kernel.elf
```

Observed no symbol output, exit 0.

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

The same command with a two-second bound and
`-kernel starter/build/kernel.elf` emitted no kernel marker and exited 124. This
is the documented incomplete UART/MMU starter behavior.

## Other bounded checks

Both isolated exercise sources passed this syntax-only command with no compiler
output, exit 0:

```sh
/usr/bin/timeout 15s \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -std=c11 -Wall -Wextra -Werror -pedantic -fsyntax-only \
  debugging/scheduler-stall/fixture.c \
  review_exercises/vm-boundary/candidate.c
```

The diagnostic benchmark was compiled but deliberately not run:

```sh
/usr/bin/timeout 30s /usr/bin/make -C benchmarks clean all \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed exit 0. No timing or `BENCHMARKED` claim is made.

## Cleanup, staging integrity, and limitations

These commands each exited 0 and removed host-linked scratch executables:

```sh
/usr/bin/make -C public_tests clean
/usr/bin/make -C sealed/reference_tests clean
/usr/bin/make -C adversarial clean
/usr/bin/make -C benchmarks clean
```

The deterministic ARM products remain under `starter/build/` and
`sealed/reference/build/`. No compiled host test/benchmark executable remains.

The staged prior tree aggregate was measured before copying and again after all
repairs using:

```sh
find PRIOR_BUILD -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

The before observation was
`680f62d2f09759ee5a74ef57d6a80d61754b7fd00eac25af76ad86a78e9c9fd5`.
The final staging and metadata hashes are recorded after the final audits below:

```text
680f62d2f09759ee5a74ef57d6a80d61754b7fd00eac25af76ad86a78e9c9fd5  PRIOR_BUILD aggregate (after)
ed341b7d2c20da194bf795ec465cf7edf394687a6cd0c9132e5c9d550aa34b90  PRIOR_REVIEW aggregate (after)
57603bb1ad65e89ec5dd75016735b93adb87dc55d0d12e6384a2b21e99176bec  MANIFEST.yaml
6a0410262aad87532cd91b268236eb2c8f52cb7ebfef93dbdba15f3a553f440d  PROVENANCE.json
```

No physical board, externally materialized learner view, transfer environment,
upstream comparison, preemptive interrupt path, userspace isolation, persistent
filesystem, multicore behavior, fuzz campaign, repeated timing study, formal
proof, security audit, or production workload was validated.
