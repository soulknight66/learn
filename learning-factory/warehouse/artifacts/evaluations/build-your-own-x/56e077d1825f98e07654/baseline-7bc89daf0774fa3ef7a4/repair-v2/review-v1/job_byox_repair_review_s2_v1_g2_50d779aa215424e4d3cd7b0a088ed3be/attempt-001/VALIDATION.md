# Independent validation evidence

Date: 2026-09-02 (America/Chicago)

Disposition: **REVISE**. `CANDIDATE/` was treated as immutable. Review probes, copied trees, binaries, logs, and materialized views were created only under review-owned workspace paths. Candidate-authored scripts were treated as test subjects, not as proof of any validation label.

Controller evidence binding: `controller-audit-sha256:9768c1e824f3afcf1d3668dbf93c7ce0c7ee31a1783e44fc0e7ee791b2461985`.

Every shell invocation emitted harmless lookup warnings for the sandbox's numeric user/group IDs. They are omitted below; command exit status and program output were unaffected.

## Tool identities

Useful configured binaries were invoked at their exact paths:

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc --version
arm-none-eabi-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203

$ /usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
    /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm --version
QEMU emulator version 9.1.1

$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-readelf --version
GNU readelf (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203

$ /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-nm --version
GNU nm (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203

$ /usr/bin/make --version
GNU Make 4.2.1
```

A preliminary QEMU `--version` invocation without the documented GLib `LD_LIBRARY_PATH` failed at dynamic loading with `undefined symbol: g_date_time_format_iso8601`. The exact environment-qualified invocation above and all QEMU executions succeeded. Java, AArch64, Node, Go, NASM, Flex, and Bison were irrelevant and were not invoked. No required ARM/QEMU/Python/GCC toolchain was unavailable.

## Candidate binding and immutable inventory

The two audited sources exactly match the controller record:

```sh
sha256sum CANDIDATE/sealed/reference/kernel/runtime.c \
  CANDIDATE/sealed/reference/kernel/scheduler.c
```

Observed exit 0:

```text
4bcb6d4619a949e0a395168434db180bc1cc7d41b490cdb65a03c6f62527e919  CANDIDATE/sealed/reference/kernel/runtime.c
8ba0e4915ed997dacb161212a7b423e927a01126b027621c927b0f0e802aab9c  CANDIDATE/sealed/reference/kernel/scheduler.c
```

Manifest and provenance documents parsed as JSON. Their submitted byte hashes are:

```text
57603bb1ad65e89ec5dd75016735b93adb87dc55d0d12e6384a2b21e99176bec  CANDIDATE/MANIFEST.yaml
6a0410262aad87532cd91b268236eb2c8f52cb7ebfef93dbdba15f3a553f440d  CANDIDATE/PROVENANCE.json
```

Independent inventory found 107 regular files, 35 directories below the pack root, and no symlinks. This deterministic aggregate was recorded before cleanup and repeated after candidate-facing checks:

```sh
find CANDIDATE -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

```text
c2bfa1de9cc883c81702889453a1d25bcc73353e8166f5867a8adafc9a5d30e5  -
```

The submission-local audit was independently invoked:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/sealed/pack_audit.py --pack-root CANDIDATE
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

This verifies what that script checks; it does not convert the builder-owned audit into a validation label.

## High-severity runtime reproduction

### Static path

`runtime.c` stores only a global runtime pointer. Its bootstrap obtains entry and argument from mutable `scheduler.current_slot` and later calls an identity-free `lf_runtime_exit()`. Yield and exit also derive the physical context-save slot from the same mutable logical slot. Meanwhile, the public scheduler API permits exit, reap, spawn, and selection without switching the currently executing ARM frame.

The reproduced sequence is:

1. PID 1 physically executes from slot 0.
2. It calls the scheduler API to become a zombie, reaps PID 1, and spawns PID 2 into slot 0.
3. It calls `lf_scheduler_rotate`, logically selecting PID 2 while PID 1's old frame still executes.
4. The old frame returns through `task_bootstrap`.
5. `lf_runtime_exit` reads logical slot 0, marks PID 2 zombie, saves stale PID 1 registers into PID 2's context, and restores boot context.

### Independent probe

The reviewer-authored temporary source had SHA-256 `fc69a848804c8afbbf955bc3f0228a705db2dfcb4d23a1b5aaa464be3ce037c5` and contained:

```c
#include "kernel/runtime.h"
#include "kernel/uart.h"

#include <stdint.h>

static lf_runtime_t runtime;
static uint8_t outer_stack[1024] __attribute__((aligned(8)));
static uint8_t replacement_stack[1024] __attribute__((aligned(8)));
static uint32_t outer_pid;
static volatile uint32_t replacement_ran;

static void replacement_task(void *argument) {
    (void)argument;
    replacement_ran = 1u;
    lf_uart_puts("REPLACEMENT-RAN\n");
}

static void outer_task(void *argument) {
    uint32_t replacement_pid;

    (void)argument;
    if (lf_scheduler_exit_current(&runtime.scheduler) != 0u ||
        !lf_scheduler_reap(&runtime.scheduler, outer_pid)) {
        lf_uart_puts("PROBE-SETUP-FAILED\n");
        return;
    }

    replacement_pid = lf_runtime_spawn(&runtime, replacement_task,
                                         (void *)0, replacement_stack,
                                         sizeof(replacement_stack));
    if (replacement_pid == 0u ||
        lf_scheduler_rotate(&runtime.scheduler) != replacement_pid) {
        lf_uart_puts("PROBE-SETUP-FAILED\n");
        return;
    }

    lf_uart_puts("OUTER-RETURN\n");
}

int kernel_main(void) {
    lf_uart_puts("REENTRANT-PROBE\n");
    lf_runtime_init(&runtime);
    outer_pid = lf_runtime_spawn(&runtime, outer_task, (void *)0,
                                 outer_stack, sizeof(outer_stack));
    if (outer_pid == 0u || !lf_runtime_start(&runtime)) {
        lf_uart_puts("PROBE-SETUP-FAILED\n");
        return 1;
    }

    if (replacement_ran == 0u) {
        lf_uart_puts("BUG-STALE-RETURN-KILLED-REPLACEMENT\n");
    } else {
        lf_uart_puts("NO-BUG\n");
    }
    return 0;
}
```

It was compiled outside `CANDIDATE/` with the submitted scheduler/runtime/UART/context sources:

```sh
/usr/bin/timeout 45s \
  /arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-gcc \
  -I CANDIDATE/sealed/reference/include \
  -std=c11 -mcpu=arm926ej-s -marm -ffreestanding -fno-builtin \
  -fno-stack-protector -fno-pic -Wall -Wextra -Werror -O2 \
  -ffunction-sections -fdata-sections -nostdlib \
  -Wl,-T,CANDIDATE/sealed/reference/arch/arm/linker.ld \
  -Wl,--gc-sections -Wl,--build-id=none -Wl,-z,noexecstack \
  -Wl,-Map,REVIEW_BUILD/reentrant_probe.map \
  REVIEW_REENTRANT_PROBE.c \
  CANDIDATE/sealed/reference/kernel/scheduler.c \
  CANDIDATE/sealed/reference/kernel/runtime.c \
  CANDIDATE/sealed/reference/kernel/uart.c \
  CANDIDATE/sealed/reference/arch/arm/start.S \
  CANDIDATE/sealed/reference/arch/arm/context.S \
  -o REVIEW_BUILD/reentrant_probe.elf
```

Observed: exit 0, no diagnostic output. The ELF SHA-256 was `9a0e4254aec68182eddf7ed20fcdca9477ce64badc0bae9f9de651c6ae2ee408`.

Bounded execution:

```sh
/usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /usr/bin/timeout 10s \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-arm \
  -M versatilepb -cpu arm926 -m 128M -nographic -monitor none \
  -semihosting-config enable=on,target=native \
  -kernel REVIEW_BUILD/reentrant_probe.elf
```

Observed QEMU exit 0 because `kernel_main` returned through semihosting. The marker result, not that process status, establishes failure:

```text
REENTRANT-PROBE
OUTER-RETURN
BUG-STALE-RETURN-KILLED-REPLACEMENT
```

The raw CRLF UART output was 68 bytes with SHA-256:

```text
08865798fa3b5544fdfc927e022f64c1d430e9d252feef2077185526f03ae7e7
```

Replacing CRLF with LF using configured Python produced 65 bytes with SHA-256:

```text
ab9b3fe67c8febba717d224c9c56d79529131bd50ab01051f5babca838bef62a
```

Those byte counts, hashes, and markers exactly reproduce the controller evidence. `REPLACEMENT-RAN` and `NO-BUG` were absent.

## Nominal ARM path and reproducibility

The submitted nominal ELF was run with the same bounded QEMU command, changing only the kernel path to `CANDIDATE/sealed/reference/build/kernel.elf`. It exited 0 and produced 75 raw bytes, SHA-256 `aaebe5746d4eeda12d2708ddc01e72dbb8d25c1b0011bcae7c7ee8fb13b068b3`:

```text
LF-KERNEL boot
mmu: on
vm: ok
ramfs: ok
tasks: ABABAB
PASS reference
```

`arm-none-eabi-readelf -h -l` observed ELF32 little-endian ARM EABI5, entry `0x10000`, one RX load segment, one RW load segment, and an RW/non-executable GNU stack. `arm-none-eabi-nm -u` emitted no symbols and exited 0.

A writable review copy was used for a clean build so the submission remained untouched:

```sh
cp -a CANDIDATE/sealed/reference REVIEW_BUILD/reference-rebuild
chmod -R u+w REVIEW_BUILD/reference-rebuild
/usr/bin/timeout 45s /usr/bin/make -C REVIEW_BUILD/reference-rebuild clean all \
  CROSS_COMPILE=/arm/tools/arm/arm-gnu-toolchain-arm-none-eabi/15.2.rel1/linux64/bin/arm-none-eabi-
```

Observed exit 0 with no compiler/linker warning. `cmp -s` found both products byte-identical to the submission:

```text
43dc67083d95cc6316da74f1811bacdd0da4d95c19cbc6244012d8fc70696d73  kernel.elf (submitted and rebuilt)
b0a152b88f7f284512f82b46453ba20b6d44146841ffe240ea13c49b1b799021  kernel.bin (submitted and rebuilt)
```

The first clean attempt on the copied tree failed because `cp -a` preserved the submission's read-only modes. Making only the review copy owner-writable resolved it; no candidate file was changed.

## Host suites and the coverage gap

Reference tests were compiled directly to review scratch with the configured host compiler, binutils prefix, AddressSanitizer, and UndefinedBehaviorSanitizer:

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ \
  -I CANDIDATE/sealed/reference/include \
  -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  CANDIDATE/sealed/reference_tests/test_reference.c \
  CANDIDATE/sealed/reference/kernel/scheduler.c \
  CANDIDATE/sealed/reference/kernel/vm.c \
  CANDIDATE/sealed/reference/kernel/ramfs.c \
  -o REVIEW_BUILD/test_reference

/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 REVIEW_BUILD/test_reference
```

Observed exit 0: `reference_tests: PASS (407 checks)`.

The same compiler flags built the adversarial vector runner from `adversarial/vector_runner.c`, `scheduler.c`, `vm.c`, and `ramfs.c`. This bounded execution exited 0:

```sh
/usr/bin/timeout 45s /usr/bin/env \
  LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
  ASAN_OPTIONS=detect_leaks=0 PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/adversarial/run_vectors.py \
  --vectors CANDIDATE/adversarial/cases/boundaries.json \
  --runner REVIEW_BUILD/vector_runner
```

Observed: `adversarial_vectors: PASS (12 vectors)`.

The public suite compiled against the reference with the same sanitizer setup and printed `public_tests: PASS`, exit 0. Compiled against the intentionally incomplete starter, it printed `public_tests: 37 check(s) failed`, exit 1, matching the documented baseline.

Bounded-runner tests were also repeated:

```sh
/usr/bin/timeout 45s /usr/bin/env \
  TMPDIR=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_repair_review_s2_v1_g2_50d779aa215424e4d3cd7b0a088ed3be/attempt-001/REVIEW_BUILD/tmp \
  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=CANDIDATE/adversarial \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest CANDIDATE/adversarial/test_run_vectors.py -v
```

Observed: all three tests `ok`, `Ran 3 tests`, `OK`, exit 0. An initial run from the read-only `CANDIDATE/adversarial` directory lacked a usable temporary directory and errored before the descendant-kill case; the explicit review-owned `TMPDIR` above resolved that environmental precondition.

Critically, the 407-check reference and 12-vector adversarial builds do not compile `runtime.c` or `arch/arm/context.S`. Their passes therefore do not exercise the identity/context bug. The nominal QEMU demo also never reaps and reuses a slot while its old frame remains active.

## Progressive disclosure and pack tests

Python policy/materializer tests:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest discover -s CANDIDATE/environment -p 'test_*.py' -v
```

Observed: all eight tests `ok`, `Ran 8 tests`, `OK`, exit 0.

Pack-audit unit tests:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=CANDIDATE/sealed \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  -m unittest CANDIDATE/sealed/test_pack_audit.py -v
```

Observed: all four tests `ok`, `Ran 4 tests`, `OK`, exit 0.

Both views were then independently materialized outside the candidate and strictly re-audited with `--list`:

```sh
/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/materialize_student_view.py \
  --source-pack CANDIDATE --destination REVIEW_BUILD/views/initial \
  --policy CANDIDATE/environment/student_view_policy.json

/usr/bin/timeout 30s /usr/bin/env PYTHONDONTWRITEBYTECODE=1 \
  /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  CANDIDATE/environment/audit_student_view.py \
  --policy CANDIDATE/environment/student_view_policy.json \
  --view REVIEW_BUILD/views/initial --list
```

Initial result: PASS, 58 entries (46 regular files and 12 directories), inventory SHA-256 `c6f8db62ce0b4ef74cad2045fb59d42c7fdb76379a5cb20e7e14923b94e19f57`.

The same two commands with destination `REVIEW_BUILD/views/post-attempt` and policy `post_attempt_view_policy.json` produced: PASS, 68 entries (52 regular files and 16 directories), inventory SHA-256 `2745e745a78d8953aff4a481e2830e0a42946b90127a5b394366df83bc96e9bb`.

Independent inventory parsing confirmed that both stages include `LICENSE_BOUNDARY.md` and neither includes any case-insensitive forbidden component (`sealed`, `reference`, `reference_tests`, `hidden_tests`, `solution`, `solutions`, or `answers`).

## Claim and provenance review

`MANIFEST.yaml` remains `GENERATED` with labels `GENERATED` and `PARTIAL`, `independent_validation: REQUIRED`, and `productionized: false`. `VALIDATION.md` explicitly disclaims promotion to `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED`. No unsupported label promotion was observed.

`LICENSE_BOUNDARY.md` clearly limits CC0-1.0 to catalog metadata, records the linked resource as `NOASSERTION`, says no linked content was copied, and gives generated material an all-rights-reserved boundary. `PROVENANCE.json`, the manifest, and the pack audit agree on project/source identifiers. With no upstream checkout or network access, the no-copy claim and linked repository license could not be independently established.

## Limitations

- The bound prior artifact tree was not present, so historical-preservation mode was not repeated.
- No physical board, transfer environment, upstream comparison, preemptive/userspace path, persistent storage, multicore behavior, production workload, fuzz campaign, repeated benchmark, formal proof, or broad security audit was performed.
- `git` and `rg` were unavailable. Deterministic `find`, `sed`, configured Python, and SHA-256 tools were used instead.
- A PASS here would still be advisory; only a separate orchestrator-captured acceptance validator may publish `REVIEWED`. This review returns REVISE because the high-severity counterexample is conclusive.
