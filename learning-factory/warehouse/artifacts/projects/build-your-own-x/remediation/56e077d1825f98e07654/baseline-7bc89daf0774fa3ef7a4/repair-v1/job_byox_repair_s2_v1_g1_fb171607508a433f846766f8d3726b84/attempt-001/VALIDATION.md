# Validation evidence

Date: 2026-09-02 (America/Chicago)

Disposition: fresh local repair-generation evidence only. `MANIFEST.yaml`
remains exactly `GENERATED` + `PARTIAL`, with independent validation required
and productionization false. These observations do not assign `BUILDS`,
`TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
`PRODUCTIONIZED`; only a worker-harness validator may promote labels.

No network access, upstream checkout, learner workspace, or student-view
materialization was attempted.

## Tool identities

Every relevant configured binary was invoked by its absolute path.

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

Java, AArch64, Node, Go, NASM, Flex, and Bison were not relevant to this C/ARM
repair and were not used. `rg` was unavailable; bounded direct reads, `find`,
and the configured Python were used instead.

## Structure, metadata, preservation, and credentials

The repair adds a deterministic evaluator-side pack audit. Its final invocation
was:

```sh
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  sealed/pack_audit.py --pack-root .
```

Observed exit 0:

```text
pack_audit: PASS
required_count=23 missing=0
forbidden_count=21 present=0
pack_regular_files=101 pack_directories=35
symlink_count=0 special_count=0
learner_forbidden_component_count=0
credential_scan=no_matches
prior_paths_preserved=94 omitted_scratch=1
repair_paths_added=7
unexpected_top_level_count=0
metadata_exactness=PASS
```

The audit strictly parsed the manifest and provenance, compared the manifest to
the authoritative nine-field object, and compared the complete provenance
object to the checksum-bound staged copy. It scanned all canonical pack roots,
not the staged prior roots or factory control directories. The only deliberately
omitted prior file is `sealed/reference_tests/build/test_reference`: it is a
path-dependent scratch executable, and the read-only `PRIOR_BUILD/` copy remains
available to the orchestrator. No top-level `LICENSE`, artifact inventory,
symlink, or special file was created.

A sorted per-file SHA-256 aggregation was taken before repair work for
`PRIOR_BUILD/` and repeated after all edits; both observations were
`0fcdab1d780a99eb1d3d3f1b5adba3d78a2fd3fd6f63cc3f8d746bcb055c604f`.
The final corresponding observation for `PRIOR_REVIEW/` was
`29d314fc103e23d235b1cc7e4ae6ee3ed8e3e448549493869b8784b5a54afd70`.
These are staging-integrity observations, not factory artifact identifiers.

Fresh file hashes after repair:

```text
57603bb1ad65e89ec5dd75016735b93adb87dc55d0d12e6384a2b21e99176bec  MANIFEST.yaml
6a0410262aad87532cd91b268236eb2c8f52cb7ebfef93dbdba15f3a553f440d  PROVENANCE.json
```

## Machine-readable adversarial coverage

The JSON now declares exactly 12 unique cases. The Python executor strictly
checks root/vector keys, types, expected results, uniqueness, and completeness;
it then invokes the C runner once per vector with an argv array and a five-second
bound. The C runner uses raw-byte snapshots for no-mutation assertions.

```sh
/usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C adversarial clean test \
  PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `adversarial_vectors: PASS (12 vectors)`, exit 0, with ASan and UBSan
active. This covers terminal and stale PIDs, duplicate and mismatched scheduler
state, exact/past 32-bit frame ends, permission subsets, translation to
`0xffffffff`, RAMFS addition wrap, full-capacity create, null/zero read, and
scrub-before-reuse. This bounded suite is not a fuzz campaign or a `FUZZED`
label.

## Portable reference and public tests

Reference initializers now canonicalize whole object representations. The
sealed suite prefilled equivalent objects with different byte patterns, checked
identical/all-zero representations after initialization, checked all bytes of a
scrubbed record, and used `memcpy` into unsigned-byte arrays for failure
snapshots.

```sh
/usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  /usr/bin/make -C sealed/reference_tests clean test \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `reference_tests: PASS (407 checks)`, exit 0.

The same sanitizer/compiler environment ran the public suite first with
`KERNEL_SRC=../sealed/reference` and then with `KERNEL_SRC=../starter`:

```text
reference: public_tests: PASS, make exit 0
starter:   public_tests: 37 check(s) failed, make exit 2
```

The starter failure is the intended staged baseline. Its safe VM/RAMFS
initializers pass the new canonical-byte checks; its behavior stubs remain
incomplete and are not a disguised solution.

Both isolated exercise sources were checked with:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -std=c11 -Wall -Wextra -Werror -pedantic -fsyntax-only \
  debugging/scheduler-stall/fixture.c \
  review_exercises/vm-boundary/candidate.c
```

Observed no compiler output, exit 0.

## Learner-view policy and audit tooling

`environment/student_view_policy.json` contains the explicit root allowlist.
Five deterministic unit tests exercise the exact allowlist, strict top-level
rejection, case-insensitive forbidden components, nonregular entry rejection,
and stable inventory digesting:

```sh
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s environment -p 'test_*.py' -v
```

Observed five tests `ok`, `Ran 5 tests`, `OK`, exit 0.

The builder audited only the allowlisted source inputs, without constructing a
student workspace:

```sh
/usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/audit_student_view.py --source-pack .
```

Observed exit 0:

```json
{"directories": 12, "entries": 55, "inventory_sha256": "d1879d8df860f1b346cd3ddfb9d0bdfe8c74bc9e2d52447995b1bdfc858abdfc", "mode": "allowlisted-source", "regular_files": 43, "status": "PASS"}
```

This establishes that current allowlisted inputs contain only regular files and
directories and no forbidden component. It does not prove that a downstream
publisher applied the allowlist. An orchestrator must materialize the exact
view, run strict `--view --list`, and retain that independent inventory; this
gate intentionally remains open and is why the pack remains `PARTIAL`.

## ARM clean builds and ELF inspection

Both output trees were rebuilt from clean directories with the configured
cross-toolchain:

```sh
/usr/bin/make -C sealed/reference clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-

/usr/bin/make -C starter clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

Both exited 0 with `-ffreestanding`, `-Wall -Wextra -Werror`, `-nostdlib`, and
no compiler/linker warning. Final retained target observations:

```text
43dc67083d95cc6316da74f1811bacdd0da4d95c19cbc6244012d8fc70696d73  sealed/reference/build/kernel.elf
b0a152b88f7f284512f82b46453ba20b6d44146841ffe240ea13c49b1b799021  sealed/reference/build/kernel.bin
fb01da0cf9457b8dc372fa52a8abcdf8d9e0e7406cf3c2105c69512591ca8ee4  starter/build/kernel.elf
a5e6978210f45b0fc27c1604276123099f26f15e2857d30a34a7d6a0b50d2f74  starter/build/kernel.bin
sealed/reference/build/kernel.elf 12516 bytes
sealed/reference/build/kernel.bin 5448 bytes
starter/build/kernel.elf 5076 bytes
starter/build/kernel.bin 120 bytes
```

Arm `readelf -h -l sealed/reference/build/kernel.elf` observed ELF32,
little-endian ARM EABI5, entry `0x10000`, one RX load, one RW load, and an
RW/non-executable GNU stack. The following emitted no symbols and exited 0:

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

Observed exit 0 and ordered serial output:

```text
LF-KERNEL boot
mmu: on
vm: ok
ramfs: ok
tasks: ABABAB
PASS reference
```

The same invocation with a two-second bound and
`starter/build/kernel.elf` emitted no kernel marker, was terminated by timeout,
and exited 124. That is the documented UART/MMU-stub baseline.

## Scratch cleanup and unvalidated scope

After the observations, these commands each exited 0 and removed host-linked
scratch products:

```sh
/usr/bin/make -C public_tests clean
/usr/bin/make -C sealed/reference_tests clean
/usr/bin/make -C adversarial clean
/usr/bin/make -C benchmarks clean
```

The deterministic ARM products remain in `starter/build/` and
`sealed/reference/build/`. No compiled test executable remains in
`public_tests/`, `adversarial/`, `benchmarks/`, or `sealed/reference_tests/`.

No physical board, externally materialized learner view, transfer environment,
upstream comparison, preemptive interrupt path, userspace isolation, hardware
small-page switching, persistent filesystem, multicore behavior, fuzzer,
repeated performance study, formal proof, security audit, or production
workload was validated.
