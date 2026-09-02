# Independent validation record

Date: 2026-09-02 (America/Chicago)

All build-producing commands ran in a private `.review-work` copy. The submitted
`CANDIDATE/` tree was never written. The copy initially retained the submission's
read-only directory modes, so the first reference-test attempt failed at
`mkdir build: Permission denied`; permissions were changed only in the copy and
the unchanged command then passed. Harmless numeric UID/GID lookup warnings
preceded shell output throughout.

## Immutable input

```sh
find CANDIDATE -type f -print0 | LC_ALL=C sort -z |
  xargs -0 sha256sum | sha256sum
```

Observed both before and after review, exit 0:

```text
5a33247391bdcc87270659fc2fb7c315bcd77268aba355789c220acb7a49f126  -
```

`find` counted 109 regular files and 36 directories including the candidate
root. No symlink, special object, or multiply linked regular file was found.

Scratch setup was:

```sh
mkdir .review-work
cp -a CANDIDATE/. .review-work/
find .review-work -type d -exec chmod u+rwx {} +
find .review-work -type f -exec chmod u+rw {} +
```

## Tool identities

Useful configured binaries were invoked at their exact paths:

```text
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0

/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc --version
arm-none-eabi-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203

LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm --version
QEMU emulator version 9.1.1

/usr/bin/make --version
GNU Make 4.2.1

/usr/bin/timeout --version
timeout (GNU coreutils) 8.30
```

No relevant ARM32, QEMU, host-C, or Python tool was unavailable. Java, AArch64,
Node, Go, NASM, Flex, and Bison were irrelevant and were not invoked.

## Host execution

Commands below were run from `.review-work/`.

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C sealed/reference_tests clean test \
  "CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/"
```

Observed exit 0: `reference_tests: PASS (407 checks)` with AddressSanitizer and
UndefinedBehaviorSanitizer enabled.

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 PYTHONDONTWRITEBYTECODE=1 \
  /usr/bin/make -C adversarial clean test \
  PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  "CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/"
```

Observed exit 0: three runner tests passed in 2.649 seconds and
`adversarial_vectors: PASS (12 vectors)`.

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C public_tests clean test \
  KERNEL_SRC=../sealed/reference \
  "CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/"
```

Observed exit 0: `public_tests: PASS`. With `KERNEL_SRC=../starter`, the same
command exited 2 after `public_tests: 37 check(s) failed`, exactly matching the
documented intentionally incomplete starter.

Publication-policy and pack-audit unit tests reported eight and four passing
tests respectively. A submission-local pack audit exited 0 with:

```text
pack_audit: PASS
required_count=23 missing=0
forbidden_count=21 present=0
pack_regular_files=109 pack_directories=35
symlink_count=0 special_count=0 hard_link_groups=0
learner_forbidden_component_count=0
credential_scan=no_matches
unexpected_top_level_count=0
manifest_exactness=PASS
provenance_consistency=PASS
historical_comparison=SKIPPED(no prior input)
```

An independent JSON assertion also confirmed identical project/source IDs and
commit across manifest/provenance and the exact conservative manifest labels.
The actual file hashes were:

```text
57603bb1ad65e89ec5dd75016735b93adb87dc55d0d12e6384a2b21e99176bec  MANIFEST.yaml
6a0410262aad87532cd91b268236eb2c8f52cb7ebfef93dbdba15f3a553f440d  PROVENANCE.json
```

## ARM builds and nominal execution

```sh
/usr/bin/timeout 45s /usr/bin/make -C sealed/reference clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
/usr/bin/timeout 45s /usr/bin/make -C starter clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

Both exited 0 without compiler/linker diagnostics. Fresh results exactly matched
the submitted evidence:

```text
6400304f127c22890440d03442df71677923578ec260a9ba5aecc9e7f929bf03  sealed/reference/build/kernel.elf  (13352 bytes)
b45307b608f48d228729f347c2ab2049ecac0674e139e7f5db0dde6534b4fb8a  sealed/reference/build/kernel.bin  (6176 bytes)
fb01da0cf9457b8dc372fa52a8abcdf8d9e0e7406cf3c2105c69512591ca8ee4  starter/build/kernel.elf           (5076 bytes)
a5e6978210f45b0fc27c1604276123099f26f15e2857d30a34a7d6a0b50d2f74  starter/build/kernel.bin            (120 bytes)
```

```sh
/usr/bin/timeout 15s \
  /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-readelf \
  -h -l sealed/reference/build/kernel.elf
/usr/bin/timeout 15s \
  /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-nm \
  -u sealed/reference/build/kernel.elf
```

Observed exit 0: ELF32 little-endian ARM EABI5, entry `0x10000`, RX and RW load
segments, RW/non-executable GNU stack, and no undefined-symbol output.

```sh
/usr/bin/timeout 10s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  -M versatilepb -cpu arm926 -m 128M -nographic -monitor none \
  -semihosting-config enable=on,target=native \
  -kernel sealed/reference/build/kernel.elf
```

Observed exit 0:

```text
LF-KERNEL boot
mmu: on
vm: ok
ramfs: ok
tasks: ABABAB
PASS reference
```

## Stale-frame repair

```sh
/usr/bin/timeout 45s /usr/bin/make -C sealed/reference_tests clean arm-test \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi- \
  PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  QEMU=/arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  QEMU_LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64
```

Observed exit 0:

```text
REENTRANT-PROBE
REPLACEMENT-RAN
RETURN-REPLACEMENT-RAN
NO-BUG
runtime_reentrancy_qemu: PASS
```

The submitted test has only one ready replacement, so a reviewer-authored ARM
probe added a second ready task. It reaped/reused the physically executing
task's slot, preselected the first replacement, invoked stale yield, asserted
that the selected task ran before the peer, and rejected stale resumption. Its
ephemeral source SHA-256 was
`a3c122313811a27633a426095d5318e7fe6101922bceb69b2610defe65aad11e`.
It was compiled from `.review-work/sealed/reference_tests/` with:

```sh
mkdir -p build
/usr/bin/timeout 45s \
  /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc \
  -I../reference/include -std=c11 -mcpu=arm926ej-s -marm \
  -ffreestanding -fno-builtin -fno-stack-protector -fno-pic \
  -Wall -Wextra -Werror -O2 -ffunction-sections -fdata-sections \
  -nostdlib -Wl,-T,../reference/arch/arm/linker.ld \
  -Wl,--gc-sections -Wl,--build-id=none -Wl,-z,noexecstack \
  -Wl,-Map,build/independent_rotation_probe.map \
  independent_rotation_probe.c ../reference/kernel/scheduler.c \
  ../reference/kernel/runtime.c ../reference/kernel/uart.c \
  ../reference/arch/arm/start.S ../reference/arch/arm/context.S \
  -o build/independent_rotation_probe.elf

/usr/bin/timeout 10s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  -M versatilepb -cpu arm926 -m 128M -nographic -monitor none \
  -semihosting-config enable=on,target=native \
  -kernel build/independent_rotation_probe.elf
```

QEMU exited 0 with:

```text
INDEPENDENT-ROTATION-PROBE
SELECTED-FIRST
OTHER-SECOND
INDEPENDENT-ROTATION-PASS
```

## Progressive disclosure

After cleaning host scratch products, source audits reproduced both recorded
digests:

```text
initial: directories=12 entries=58 regular_files=46
         81f63fcd250423fec3be23225a873be2505cf4e054d2e5c879ce630b3678b064
post:    directories=16 entries=68 regular_files=52
         278b58719eb95f6cbf06deec5b751c3f826106ec9b7cb2e402018174b1d7f6bc
```

Unlike the builder evidence, this review then actually materialized both stages:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/materialize_student_view.py \
  --source-pack . --destination ../.review-initial-view \
  --policy environment/student_view_policy.json

/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/materialize_student_view.py \
  --source-pack . --destination ../.review-post-view \
  --policy environment/post_attempt_view_policy.json
```

Strict `--view` audits exited 0 and reproduced the same counts and hashes.
Independent `find` inventory plus `diff -qr` showed that the views otherwise
matched and that the post-attempt stage added exactly `debugging/` and
`review_exercises/`, containing six allowlisted files and four directories.
Neither view contained a sealed answer/reference path. Both policies omit
`PROVENANCE.json`, even though learner-visible `LICENSE_BOUNDARY.md` refers to it.

## Harness failure-mode check

Static inspection found that `run_runtime_qemu.py` calls `communicate()` before
testing `len(output) > MAX_OUTPUT`. A reviewer-authored executable wrote 1024
chunks of 8192 bytes (8 MiB) and exited. Its source SHA-256 was
`8046e88ead93784df163db8cd67bf118de967b9ee5cda78cd5117af6ba6b5b64`.

```sh
/usr/bin/time -f 'maximum_resident_kib=%M command_exit=%x' \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  run_runtime_qemu.py \
  --qemu /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v2_g2_219042700e8392cd6591bd6441ff449d/attempt-001/.review-work/sealed/reference_tests/fake_qemu_flood.py \
  --kernel /projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v2_g2_219042700e8392cd6591bd6441ff449d/attempt-001/.review-work/sealed/reference_tests/fake_qemu_flood.py \
  --timeout 5 > /dev/null
```

Observed only after the producer completed:

```text
runtime_reentrancy_qemu: FAIL: captured output exceeds 65536 bytes
maximum_resident_kib=28088 command_exit=1
```

The rejection is correct but post-hoc; retained memory scales with producer
output until exit or timeout rather than with the stated 65,536-byte limit.

## Limitations and cleanup

`PRIOR_BUILD`, the controller audit body, and an immutable upstream snapshot were
absent. Their preservation/originality claims are therefore inconclusive. QEMU
is not physical-board evidence. No fuzz, benchmark, formal, broad-security, or
production evaluation was attempted. Candidate-authored suites are observations,
not label-promotion authority. Reviewer scratch copies and both materialized
views were removed after recording results.
