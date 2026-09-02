# Validation evidence

Date: 2026-09-02 (America/Chicago)

Disposition: fresh repair-generation-2, policy-version-2 builder evidence.
`MANIFEST.yaml` remains exactly `GENERATED` + `PARTIAL`, requires independent
validation, and keeps `productionized` false. These observations do not assign
`BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`,
`TRANSFER_VERIFIED`, or `PRODUCTIONIZED`; only a worker-harness validator may
promote labels.

The repair is bound to controller audit
`9768c1e824f3afcf1d3668dbf93c7ce0c7ee31a1783e44fc0e7ee791b2461985`
and prior builder artifact
`3b4dc34ca41ad7e72504f7c0c9d5f3f7285ad4032b7dab80e344ee3e509d265d`.
No network access, upstream checkout, learner workspace, physical board, or
actual learner-view materialization was used. The environment unit test creates
and removes only a synthetic miniature filesystem fixture.

Every shell invocation emitted harmless lookup warnings for the sandbox's
numeric user/group IDs. They are omitted from snippets below; recorded command
statuses and program output were unaffected.

## Repair scope

The runtime now records the physically executing frame as a slot and PID pair,
and records a PID owner for every per-slot ARM context. Bootstrap captures that
identity before entering task code. Yield and exit mutate the logical current
only when it is still that physical identity. If reentrant policy activity has
already selected a replacement, the runtime dispatches it without another
rotation. A stale frame whose slot was reaped and reused saves only to a
dedicated discard context, never to the replacement's initialized context.

The new sealed ARM regression covers both paths from the audit:

1. stale physical code calls runtime yield after exit/reap/reuse/selection and
   must never resume after that call;
2. stale physical code returns after exit/reap/reuse/selection and its bootstrap
   must dispatch, rather than exit, the replacement.

Learner-visible requirements and design prompts describe the identity invariant
without publishing reference code. Sealed rationale and review material explain
the implementation. `sealed/prior_baseline.json` now binds the supplied
`PRIOR_BUILD/` content digest and immutable artifact identifiers.

## Tool identities

Useful configured binaries were invoked at their exact paths:

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

Java, AArch64, Node, Go, NASM, Flex, and Bison were irrelevant and were not
invoked. No required ARM, QEMU, Python, or host-C tool was unavailable.

## ARM stale-frame regression

```sh
/usr/bin/timeout 45s /usr/bin/make -C sealed/reference_tests clean arm-test \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi- \
  PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  QEMU=/arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  QEMU_LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64
```

Observed: cross-compilation exited 0 with no diagnostic, QEMU exited 0 within
the runner's 10-second bound, the process-session runner exited 0, and output
was:

```text
REENTRANT-PROBE
REPLACEMENT-RAN
RETURN-REPLACEMENT-RAN
NO-BUG
runtime_reentrancy_qemu: PASS
```

`OUTER-RETURN`, `BUG-STALE-RETURN-KILLED-REPLACEMENT`, and
`PROBE-SETUP-FAILED` were absent. Before explicit scratch cleanup, observed
hashes were:

```text
170b6a4d06ddc432763bf321cc86e3ada7e608703cd6e6e23eb45673148e1e7a  sealed/reference_tests/build/runtime_reentrancy.elf
11fc36a3c746a2601d0ea5e258c8df33f54f7b4debafa9aabe8a484587f08217  sealed/reference_tests/runtime_reentrancy.c
05b10a23a8917877bedc690661a9ea4b82a9168c31424673781bd77cf236fd64  sealed/reference/kernel/runtime.c
7d2c11bc750db0e93bb125ce0478cd6834da52bb38f1f886032ba38a0a9cc8a5  sealed/reference/include/kernel/runtime.h
```

The ELF hash is transient evidence; the retained source and exact command
reproduce it. This candidate-authored runner is test material, not independent
acceptance evidence.

## ARM builds, ELF inspection, and nominal boot

```sh
/usr/bin/timeout 45s /usr/bin/make -C sealed/reference clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-

/usr/bin/timeout 45s /usr/bin/make -C starter clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

Both builds exited 0 with no compiler or linker warning. Retained artifact
observations were:

```text
6400304f127c22890440d03442df71677923578ec260a9ba5aecc9e7f929bf03  sealed/reference/build/kernel.elf
b45307b608f48d228729f347c2ab2049ecac0674e139e7f5db0dde6534b4fb8a  sealed/reference/build/kernel.bin
fb01da0cf9457b8dc372fa52a8abcdf8d9e0e7406cf3c2105c69512591ca8ee4  starter/build/kernel.elf
a5e6978210f45b0fc27c1604276123099f26f15e2857d30a34a7d6a0b50d2f74  starter/build/kernel.bin
sealed/reference/build/kernel.elf 13352 bytes
sealed/reference/build/kernel.bin  6176 bytes
starter/build/kernel.elf            5076 bytes
starter/build/kernel.bin             120 bytes
```

```sh
/usr/bin/timeout 15s \
  /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-readelf \
  -h -l sealed/reference/build/kernel.elf
```

Observed exit 0: ELF32, little-endian ARM EABI5, entry `0x10000`, one
read/execute load segment, one read/write load segment, and a read/write,
non-executable GNU stack.

```sh
/usr/bin/timeout 15s \
  /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-nm \
  -u sealed/reference/build/kernel.elf
```

Observed no symbol output, exit 0.

```sh
/usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /usr/bin/timeout 10s \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  -M versatilepb -cpu arm926 -m 128M -nographic -monitor none \
  -semihosting-config enable=on,target=native \
  -kernel sealed/reference/build/kernel.elf
```

Observed QEMU exit 0:

```text
LF-KERNEL boot
mmu: on
vm: ok
ramfs: ok
tasks: ABABAB
PASS reference
```

## Deterministic host tests

Portable reference suite:

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C sealed/reference_tests clean test \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `reference_tests: PASS (407 checks)`, exit 0, with AddressSanitizer
and UndefinedBehaviorSanitizer enabled.

Adversarial vectors and bounded-runner tests:

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 PYTHONDONTWRITEBYTECODE=1 \
  /usr/bin/make -C adversarial clean test \
  PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed: three Python tests `ok`, `Ran 3 tests`, `OK`, then
`adversarial_vectors: PASS (12 vectors)`; exit 0. This is deterministic vector
coverage, not fuzzing.

Publication-policy tests:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s environment -p 'test_*.py' -v
```

Observed all eight tests `ok`, `Ran 8 tests`, `OK`, exit 0.

Pack-audit tests:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=sealed \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest sealed/test_pack_audit.py -v
```

A preliminary run overlapped the publication-policy test's synthetic temporary
fixture. The strict current-pack case correctly rejected transient top-level
`tmponimxavi`; that run reported three tests `ok`, one error, and exited 1.
The fixture's owning test removed it. An isolated rerun of the exact command
reported all four tests `ok`, `Ran 4 tests`, `OK`, exit 0. No temporary
name was added to the allowlist.

Public suite against the reference:

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C public_tests clean test KERNEL_SRC=../sealed/reference \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `public_tests: PASS`, exit 0.

The same command with `KERNEL_SRC=../starter` reported
`public_tests: 37 check(s) failed`; make exited 2. This is the expected
intentionally incomplete starter, not passing starter evidence.

## Learner-disclosure source audits

After host-linked scratch cleanup, both allowlisted source selections were
audited without creating a learner view:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/audit_student_view.py \
  --policy environment/student_view_policy.json --source-pack .
```

Observed exit 0:

```json
{"directories": 12, "entries": 58, "inventory_sha256": "81f63fcd250423fec3be23225a873be2505cf4e054d2e5c879ce630b3678b064", "mode": "allowlisted-source", "regular_files": 46, "stage": "initial", "status": "PASS"}
```

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/audit_student_view.py \
  --policy environment/post_attempt_view_policy.json --source-pack .
```

Observed exit 0:

```json
{"directories": 16, "entries": 68, "inventory_sha256": "278b58719eb95f6cbf06deec5b751c3f826106ec9b7cb2e402018174b1d7f6bc", "mode": "allowlisted-source", "regular_files": 52, "stage": "post-attempt-exercises", "status": "PASS"}
```

These are source-selection checks, not publication evidence.

## Final structure, preservation, and credential audit

Submission-local audit:

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
pack_regular_files=109 pack_directories=35
symlink_count=0 special_count=0 hard_link_groups=0
learner_forbidden_component_count=0
credential_scan=no_matches
unexpected_top_level_count=0
manifest_exactness=PASS
provenance_consistency=PASS
historical_comparison=SKIPPED(no prior input)
```

Bound prior-preservation audit:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/pack_audit.py --pack-root . --prior-root PRIOR_BUILD \
  --prior-record sealed/prior_baseline.json
```

Observed exit 0:

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
historical_comparison=PERFORMED
prior_content_sha256=2575be7cf0f50c0a0f6327f11e3a1757173d40016bb3a34d0db11a5fc92c2e13
prior_artifact_checksum_recorded=3b4dc34ca41ad7e72504f7c0c9d5f3f7285ad4032b7dab80e344ee3e509d265d
prior_regular_files=107
prior_files_omitted=0
prior_directories=35
prior_directories_omitted=0
repair_files_added=2
prior_files_modified=21
```

The immutable manifest and provenance documents remained byte-identical to
`PRIOR_BUILD/` and had these hashes:

```text
57603bb1ad65e89ec5dd75016735b93adb87dc55d0d12e6384a2b21e99176bec  MANIFEST.yaml
6a0410262aad87532cd91b268236eb2c8f52cb7ebfef93dbdba15f3a553f440d  PROVENANCE.json
```

Scratch products created under `adversarial/build`, `public_tests/build`,
`sealed/reference_tests/build`, and `benchmarks/build` were explicitly
removed with each directory's `make clean` target. Repaired reference and
unchanged starter ARM build artifacts were retained.

## Limitations

No upstream comparison, physical ARM execution, preemption/userspace path,
production workload, fuzz campaign, benchmark study, formal proof, broad
security audit, or independent acceptance run was performed. The target-level
probe covers the specific controller counterexample and ordinary cooperative
boot path. The pack therefore remains `GENERATED` + `PARTIAL` pending fresh
independent review.
