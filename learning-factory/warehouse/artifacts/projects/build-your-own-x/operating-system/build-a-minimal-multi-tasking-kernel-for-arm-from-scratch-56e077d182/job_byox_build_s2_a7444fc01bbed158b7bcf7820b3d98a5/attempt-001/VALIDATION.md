# Validation evidence

Date: 2026-09-02 (America/Chicago)

Disposition: local generation evidence only. `MANIFEST.yaml` remains exactly
`GENERATED` + `PARTIAL`, with `independent_validation: REQUIRED` and
`productionized: false`. The observations below do not self-assign `BUILDS`,
`TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or
`PRODUCTIONIZED`; only the worker harness may promote those labels.

No network access or upstream checkout was attempted.

## Tool identities

Every relevant configured tool was invoked by absolute path.

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0
exit 0

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43
exit 0

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc --version
arm-none-eabi-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203
exit 0

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-readelf --version
GNU readelf (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
exit 0

$ /usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm --version
QEMU emulator version 9.1.1
exit 0
```

## Informative environment failures retained

The first direct QEMU version probe omitted the configured GLib root:

```text
$ /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm --version
... undefined symbol: g_date_time_format_iso8601
exit 127
```

The first isolated host-GCC test link omitted the configured Binutils search
prefix and ended with `collect2: fatal error: cannot find 'ld'` (make exit 2).
Adding `-B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/` compiled the test, but
running without the GCC runtime library root failed to load `libasan.so.8`
(make exit 2). Adding that library root started AddressSanitizer; LeakSanitizer
then reported that it cannot operate under the sandbox's tracing restriction.
Final host runs therefore set `ASAN_OPTIONS=detect_leaks=0`. AddressSanitizer and
UndefinedBehaviorSanitizer remained compiled and active. The tested kernel uses
no dynamic allocation.

Two early code-build failures were also retained during generation: the
reference RAMFS initially lacked `<stdbool.h>`, and ARM GCC rejected an
always-false enum lower-bound comparison under `-Werror`. Both were corrected
before all final commands below.

## Metadata

Strict JSON parsing used the configured Python above. The command loaded both
files, compared `MANIFEST.yaml` to the complete authoritative nine-field object,
asserted the exact seven top-level provenance keys, matched snapshot/project
identifiers, and confirmed `linked_content_copied` is false.

```text
json_validation=PASS
exit 0

$ sha256sum MANIFEST.yaml PROVENANCE.json
57603bb1ad65e89ec5dd75016735b93adb87dc55d0d12e6384a2b21e99176bec  MANIFEST.yaml
6a0410262aad87532cd91b268236eb2c8f52cb7ebfef93dbdba15f3a553f440d  PROVENANCE.json
```

The file hashes are packaging observations. The manifest's
`provenance_sha256` is the immutable snapshot identifier and is not represented
as a raw pretty-printed-file hash.

## ARM clean builds

Both build commands ran after `clean` with the configured cross prefix:

```sh
make -C starter clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-

make -C sealed/reference clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

Observed: both exited 0, compiled with `-Wall -Wextra -Werror`, linked with
`-nostdlib`, and produced ELF plus raw binary. The final command output contained
no compiler or linker warning.

Final artifact observations:

```text
e2fbf1dabd0d0eb9df8d89ae2ba65ffc2c8fe1119c66ef90673b2238d5014540  sealed/reference/build/kernel.elf
77fe608a4e066189c27f15e686e606bb20ba9efb1e55bca9f801ba850580d103  sealed/reference/build/kernel.bin
fb01da0cf9457b8dc372fa52a8abcdf8d9e0e7406cf3c2105c69512591ca8ee4  starter/build/kernel.elf
sealed/reference/build/kernel.elf 12588 bytes
sealed/reference/build/kernel.bin 5520 bytes
starter/build/kernel.elf 5076 bytes
```

`arm-none-eabi-readelf -h -l sealed/reference/build/kernel.elf` observed ELF32,
little-endian ARM EABI5, executable type, entry `0x10000`, an RX load segment, an
RW load segment, and an RW (non-executable) `GNU_STACK` header.
`arm-none-eabi-nm -u sealed/reference/build/kernel.elf` emitted no symbols and
exited 0.

## Host tests

Final sanitizer environment and compiler command:

```sh
/usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  make -C public_tests clean test \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/' \
  KERNEL_SRC=../sealed/reference
```

Observed `public_tests: PASS`, exit 0.

```sh
/usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 \
  make -C sealed/reference_tests clean test \
  CC='/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/'
```

Observed `reference_tests: PASS (400 checks)`, exit 0.

The untouched starter was also compiled against the same public suite. It
reported `public_tests: 37 check(s) failed` and make exited 2. This is expected:
the starter contains explicit safe-failure stage stubs and is not a disguised
solution.

Both isolated exercise C files were checked with:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c11 -Wall -Wextra -Werror -pedantic -fsyntax-only \
  debugging/scheduler-stall/fixture.c \
  review_exercises/vm-boundary/candidate.c
```

Observed no output, exit 0.

## Emulated target execution

Final bounded reference command:

```sh
/usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /usr/bin/timeout 10s \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  -M versatilepb -cpu arm926 -m 128M -nographic -monitor none \
  -semihosting-config enable=on,target=native \
  -kernel sealed/reference/build/kernel.elf
```

Exact serial output (terminal rendering removed CR characters):

```text
LF-KERNEL boot
mmu: on
vm: ok
ramfs: ok
tasks: ABABAB
PASS reference
```

Observed exit 0. This run crosses reset/BSS initialization, PL011 MMIO, CP15 MMU
enable, software VM/RAMFS checks, independent task stacks, ARM assembly context
switches, task-return cleanup, and the semihosted final exit.

The same command with a 2-second bound and `starter/build/kernel.elf` printed no
kernel text, was terminated by timeout, and exited 124. That is the expected
observable baseline because starter UART and MMU functions are stubs.

## Diagnostic benchmark (not a benchmark label)

The harness built with the configured GCC/Binutils command and exited 0. One
uncontrolled shared-host diagnostic run produced:

```text
iterations=100000 elapsed_ns=1543107 checksum=0
```

There were no repetitions, dispersion analysis, target execution, or acceptance
threshold. This raw observation is explicitly insufficient for `BENCHMARKED`.

## Structure, isolation, and credential checks

A shell loop tested all 23 authoritative required paths with `test -f`, all 21
forbidden paths with both existence and symlink checks, and recursively checked
the generated roots for objects other than regular files/directories. A separate
learner-tree search rejected directories named `sealed`, `reference`,
`reference_tests`, `solution`, `solutions`, `answers`, or `hidden_tests` beneath
`starter/`, `public_tests/`, and `environment/`.

Final observed results:

```text
required_count=23 missing=0
forbidden_count=21 present=0
symlink_or_special_count=0
learner_solution_directory_count=0
```

The generated text/source roots were scanned recursively (binaries excluded)
for AWS access-key form, PEM private-key headers, OpenAI-style secret form,
GitHub token forms, and Google API-key form using extended regular expressions.
Observed `credential_scan=no_matches`, exit 0.

After recording test and diagnostic output, `make -C public_tests clean` and
`make -C benchmarks clean` both exited 0. This explicitly removed scratch
executables that had been linked to sealed reference units, so no compiled
solution material remains in learner-visible `public_tests/` or the supplemental
benchmark tree. ARM starter products remain learner-safe stubs; reference
products and reference-test binaries remain only below `sealed/`.

## Unvalidated and out of scope

No physical ARM board, preemptive interrupt path, userspace isolation, hardware
small-page switching, persistent filesystem, multicore behavior, network input,
fuzzer, repeated performance study, transfer environment, formal proof,
production workload, or security audit was run. Independent validation remains
mandatory.
