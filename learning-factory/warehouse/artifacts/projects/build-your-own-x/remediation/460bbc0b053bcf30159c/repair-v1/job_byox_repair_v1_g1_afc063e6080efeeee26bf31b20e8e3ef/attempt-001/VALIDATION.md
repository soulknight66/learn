# Validation record

Date: 2026-08-31 (America/Chicago)

This is fresh worker-local evidence from repair generation 1. No result copied from `PRIOR_BUILD/`
or `PRIOR_REVIEW/` is treated as validation evidence. The authoritative status remains `GENERATED`
with labels `GENERATED` and `PARTIAL`; independent validation is still required. No `BUILDS`,
`TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is
claimed.

Commands below were run from the challenge root in the configured login environment. Each login
shell also printed three workspace diagnostics stating that numeric user/group IDs have no local
names. Those diagnostics preceded project output and did not alter the reported command exit codes.

## Repair scope and staged-input integrity

The staged inputs were hashed before copying or editing and again after all generated-pack work:

```sh
find PRIOR_BUILD -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
find PRIOR_REVIEW -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum
```

Observed both times, with exit code `0`:

```text
8e75fb9011fe1043379ef7e5920ca677074da9044286f540fc719535101da58f  -
040aaf9f31156d69f0d4eb85237a4fd6f16d1c4e1d0a2b466e3ca6c58379a9bf  -
```

After excluding this fresh validation record, a recursive comparison checked preservation of every
staged top-level pack entry:

```sh
for entry in $(find PRIOR_BUILD -mindepth 1 -maxdepth 1 -printf '%f\n' | sort); do
    if [ "$entry" = VALIDATION.md ]; then
        continue
    fi
    diff -qr "PRIOR_BUILD/$entry" "$entry"
done
```

Observed exit code: `0`. The only output was the two intended repaired answer files:

```text
Files PRIOR_BUILD/sealed/debugging/02-dual-running/ANSWER.md and sealed/debugging/02-dual-running/ANSWER.md differ
Files PRIOR_BUILD/sealed/review_exercises/01-scheduler/ANSWER.md and sealed/review_exercises/01-scheduler/ANSWER.md differ
```

## Tool availability

```sh
for tool in python3 cc gcc make ar ld nm objcopy clang valgrind cppcheck \
  clang-tidy scan-build splint qemu-system-i386 qemu-system-x86_64 nasm; do
    tool_path=$(command -v "$tool" 2>/dev/null || true)
    if [ -n "$tool_path" ]; then
        printf '%s=%s\n' "$tool" "$tool_path"
    else
        printf '%s=UNAVAILABLE\n' "$tool"
    fi
done
python3 --version
cc --version | sed -n '1p'
make --version | sed -n '1p'
```

Observed exit code: `0`.

```text
python3=/usr/bin/python3
cc=/usr/bin/cc
gcc=/usr/bin/gcc
make=/usr/bin/make
ar=/usr/bin/ar
ld=/usr/bin/ld
nm=/usr/bin/nm
objcopy=/usr/bin/objcopy
clang=UNAVAILABLE
valgrind=UNAVAILABLE
cppcheck=UNAVAILABLE
clang-tidy=UNAVAILABLE
scan-build=UNAVAILABLE
splint=UNAVAILABLE
qemu-system-i386=UNAVAILABLE
qemu-system-x86_64=UNAVAILABLE
nasm=UNAVAILABLE
Python 3.6.8
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
GNU Make 4.2.1
```

## Builds and supplied tests

```sh
timeout 30s make -C starter clean build
```

Observed exit code: `0`. GCC compiled all three starter sources with
`-std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding`, and `ar` created
`starter/build/libmicaos.a`.

```sh
timeout 30s make -C starter test
```

Observed exit code: `2`, the documented result for the deliberately incomplete learner starter:

```text
[PASS] initializers and constants
[PASS] scheduler validation
[PASS] VM validation
[PASS] RAMFS validation
    line 222: mica_scheduler_spawn(&scheduler, &first) == MICA_OK
[FAIL] scheduler lifecycle
    line 258: mica_vm_map(&vm, &space, 2u, true) == MICA_OK
[FAIL] VM lifecycle
    line 285: mica_ramfs_create(&fs, "note") == MICA_OK
[FAIL] RAMFS lifecycle

4 passed, 3 failed
make: *** [Makefile:32: test] Error 1
```

```sh
timeout 30s make -C sealed/reference clean test
```

Observed exit code: `0`. The target byte-compared the public headers, compiled all three reference
sources with the strict C11 freestanding flags, linked the hosted test, and printed:

```text
reference tests: PASS
```

The public suite was separately linked to the sealed archive and bounded when run:

```sh
cc -Isealed/reference/include -std=c11 -Wall -Wextra -Werror -pedantic \
  public_tests/test_public.c sealed/reference/build/libmicaos.a \
  -o sealed/reference/build/test_public_against_reference
timeout 30s sealed/reference/build/test_public_against_reference
```

Both commands exited `0`:

```text
[PASS] initializers and constants
[PASS] scheduler validation
[PASS] VM validation
[PASS] RAMFS validation
[PASS] scheduler lifecycle
[PASS] VM lifecycle
[PASS] RAMFS lifecycle

7 passed, 0 failed
```

```sh
nm -u sealed/reference/build/libmicaos.a
```

Observed exit code: `0`; the three object headings had no undefined symbols:

```text
scheduler.o:

vm.o:

ramfs.o:
```

## Scheduler-answer remediation checks

This textual check rejects the nonexistent backticked `current` field in exactly the two repaired
answers and displays their cursor/invariant statements:

```sh
if grep -nF '`current`' sealed/debugging/02-dual-running/ANSWER.md \
  sealed/review_exercises/01-scheduler/ANSWER.md; then
    exit 1
fi
grep -nE '`cursor`|`RUNNING`|scheduling history|state invariant' \
  sealed/debugging/02-dual-running/ANSWER.md \
  sealed/review_exercises/01-scheduler/ANSWER.md
```

Observed exit code: `0`. The first command printed nothing. The second showed that both answers use
`cursor`, that the debugging answer calls it scheduling history and permits zero `RUNNING` records,
and that the review answer states the at-most-one invariant rather than cursor/current equivalence.

The following bounded probe independently exercised the precise state semantics described by the
repair. Its source was supplied on standard input, and only its binary was written under the scratch
`build/` directory:

```sh
cc -Isealed/reference/include -std=c11 -Wall -Wextra -Werror -pedantic \
  -x c - -x none sealed/reference/build/libmicaos.a \
  -o sealed/reference/build/cursor_persistence_probe <<'EOF'
#include "micaos.h"

#include <stdio.h>

static size_t running_count(const mica_scheduler_t *scheduler)
{
    size_t count = 0u;
    size_t i;

    for (i = 0u; i < MICA_MAX_PROCESSES; i++) {
        if (scheduler->processes[i].state == MICA_PROCESS_RUNNING) {
            count++;
        }
    }
    return count;
}

int main(void)
{
    mica_scheduler_t scheduler;
    mica_pid_t pid = 0u;
    mica_pid_t selected = 0u;
    size_t scheduled_slot;
    int exit_code = 0;

    mica_scheduler_init(&scheduler);
    if (mica_scheduler_spawn(&scheduler, &pid) != MICA_OK ||
        mica_scheduler_schedule(&scheduler, &selected) != MICA_OK ||
        selected != pid) {
        return 1;
    }
    scheduled_slot = scheduler.cursor;
    if (scheduler.processes[scheduled_slot].state != MICA_PROCESS_RUNNING ||
        running_count(&scheduler) != 1u) {
        return 2;
    }
    if (mica_scheduler_block(&scheduler, pid) != MICA_OK ||
        scheduler.cursor != scheduled_slot ||
        scheduler.processes[scheduled_slot].state != MICA_PROCESS_BLOCKED ||
        running_count(&scheduler) != 0u) {
        return 3;
    }
    if (mica_scheduler_wake(&scheduler, pid) != MICA_OK ||
        mica_scheduler_schedule(&scheduler, &selected) != MICA_OK ||
        scheduler.cursor != scheduled_slot ||
        running_count(&scheduler) != 1u) {
        return 4;
    }
    if (mica_scheduler_exit(&scheduler, pid, 23) != MICA_OK ||
        scheduler.cursor != scheduled_slot ||
        scheduler.processes[scheduled_slot].state != MICA_PROCESS_EXITED ||
        running_count(&scheduler) != 0u) {
        return 5;
    }
    if (mica_scheduler_reap(&scheduler, pid, &exit_code) != MICA_OK ||
        exit_code != 23 ||
        scheduler.cursor != scheduled_slot ||
        scheduler.processes[scheduled_slot].state != MICA_PROCESS_UNUSED ||
        running_count(&scheduler) != 0u) {
        return 6;
    }

    (void)printf("cursor persistence probe: PASS (slot=%zu)\n", scheduled_slot);
    return 0;
}
EOF
timeout 30s sealed/reference/build/cursor_persistence_probe
```

The compile and run each exited `0`:

```text
cursor persistence probe: PASS (slot=0)
```

Thus the executable observation covers a successful scheduling decision followed by block, wake,
reschedule, exit, and reap. In particular, block, exit, and reap leave `cursor` at slot 0 while the
number of `RUNNING` records becomes zero.

## Scratch cleanup

```sh
make -C starter clean
make -C sealed/reference clean
find starter sealed/reference -type d -name build -print
```

Observed exit code: `0`. Both Makefiles removed their explicit `build/` directories, and the final
`find` printed nothing.

## Final deterministic archive audit

The following audit is scoped to generated challenge-pack roots, not controller-owned staging and
workspace metadata:

```sh
python3 - <<'PY'
import json
import os
import stat

required = [
    "README.md", "AGENTS.md", "MANIFEST.yaml", "PROVENANCE.json",
    "LICENSE_BOUNDARY.md", "REQUIREMENTS.md", "CONCEPTS.md",
    "DESIGN_QUESTIONS.md", "VALIDATION.md", "starter/README.md",
    "public_tests/README.md", "environment/README.md",
    "sealed/reference/README.md", "sealed/reference_tests/README.md",
    "sealed/DESIGN.md", "sealed/TRADEOFFS.md", "sealed/REVIEW.md",
    "sealed/alternatives/README.md",
    "sealed/production/PRODUCTIONIZATION.md", "adversarial/README.md",
    "debugging/README.md", "review_exercises/README.md",
    "benchmarks/README.md",
]
forbidden = [
    ".git", ".env", ".venv", "credentials.json", "secrets", "reference",
    "reference_tests", "hidden_tests", "solution", "solutions", "answers",
    "starter/sealed", "starter/reference", "starter/reference_tests",
    "starter/solution", "starter/solutions", "starter/answers",
    "public_tests/sealed", "public_tests/reference", "public_tests/hidden_tests",
    "environment/sealed",
]
expected_manifest = {
    "independent_validation": "REQUIRED",
    "productionized": False,
    "project_id": "project_9f93e5b30db7d5e4adf5244cd9ccb1b0",
    "provenance_sha256":
        "12d6d6c4f85287f0d3fd4bb2beeef0a10e72eac5c5016cb2e5b83348340fb516",
    "schema_version": 1,
    "source_commit": "aa17439b62f384511a5561ce308e9598b94d8989",
    "source_id": "source_eac489a34bed5db9a1f2a580b457bcef",
    "status": "GENERATED",
    "validation_labels": ["GENERATED", "PARTIAL"],
}

def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result

def reject_constant(value):
    raise ValueError("non-finite JSON number: " + value)

def strict_json(path):
    with open(path, "r") as handle:
        return json.load(handle, object_pairs_hook=no_duplicates,
                         parse_constant=reject_constant)

missing = [path for path in required
           if not os.path.isfile(path) or os.path.islink(path)]
present_forbidden = [path for path in forbidden if os.path.lexists(path)]
if missing or present_forbidden:
    raise SystemExit("path audit failed: missing={!r} forbidden={!r}".format(
        missing, present_forbidden))

pack_roots = sorted(os.listdir("PRIOR_BUILD"))
special = []
regular_count = 0
for root in pack_roots:
    paths = [root]
    if os.path.isdir(root) and not os.path.islink(root):
        for directory, directories, files in os.walk(root):
            paths.extend(os.path.join(directory, name) for name in directories)
            paths.extend(os.path.join(directory, name) for name in files)
    for path in paths:
        mode = os.lstat(path).st_mode
        if stat.S_ISREG(mode):
            regular_count += 1
        elif not stat.S_ISDIR(mode):
            special.append(path)
if special:
    raise SystemExit("special generated entries: {!r}".format(special))

manifest = strict_json("MANIFEST.yaml")
provenance = strict_json("PROVENANCE.json")
prior_provenance = strict_json("PRIOR_BUILD/PROVENANCE.json")
if manifest != expected_manifest:
    raise SystemExit("manifest mismatch")
if provenance != prior_provenance:
    raise SystemExit("provenance differs from checksum-bound prior")
if provenance.get("snapshot_sha256") != expected_manifest["provenance_sha256"]:
    raise SystemExit("provenance digest mismatch")
with open("starter/include/micaos.h", "rb") as left:
    starter_header = left.read()
with open("sealed/reference/include/micaos.h", "rb") as right:
    reference_header = right.read()
if starter_header != reference_header:
    raise SystemExit("public headers differ")

print("required regular files: {}/{}".format(len(required), len(required)))
print("forbidden paths present: 0")
print("symlinks or special generated entries: 0")
print("generated regular files: {}".format(regular_count))
print("MANIFEST.yaml: strict JSON and exact expected object")
print("PROVENANCE.json: strict JSON and equal to checksum-bound prior")
print("starter/reference headers: byte-identical")
PY
```

Observed exit code: `0`.

```text
required regular files: 23/23
forbidden paths present: 0
symlinks or special generated entries: 0
generated regular files: 42
MANIFEST.yaml: strict JSON and exact expected object
PROVENANCE.json: strict JSON and equal to checksum-bound prior
starter/reference headers: byte-identical
```

## Credential-pattern scan

```sh
python3 - <<'PY'
import os
import re

patterns = [
    re.compile(br"AKIA[0-9A-Z]{16}"),
    re.compile(br"gh[pousr]_[A-Za-z0-9]{36,255}"),
    re.compile(br"sk-[A-Za-z0-9]{20,}"),
    re.compile(br"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(br"(?i)\b(?:password|passwd|api[_-]?key|secret|token)\b"
               br"\s*[:=]\s*[\"']?[A-Za-z0-9_./+=-]{8,}"),
]

pack_roots = sorted(os.listdir("PRIOR_BUILD"))
files = []
for root in pack_roots:
    if os.path.isfile(root) and not os.path.islink(root):
        files.append(root)
    elif os.path.isdir(root) and not os.path.islink(root):
        for directory, directories, names in os.walk(root):
            directories[:] = [name for name in directories
                              if not os.path.islink(os.path.join(directory, name))]
            files.extend(os.path.join(directory, name) for name in names
                         if os.path.isfile(os.path.join(directory, name)) and
                         not os.path.islink(os.path.join(directory, name)))

matches = []
for path in files:
    with open(path, "rb") as handle:
        data = handle.read()
    if any(pattern.search(data) for pattern in patterns):
        matches.append(path)
if matches:
    raise SystemExit("credential-pattern matches: {!r}".format(matches))
print("credential-pattern scan: 0 matches across {} generated regular files".format(
    len(files)))
PY
```

Observed exit code: `0`.

```text
credential-pattern scan: 0 matches across 42 generated regular files
```

## Scope and remaining blockers

- QEMU, NASM, a cross toolchain, a second compiler, Valgrind, and the listed static analyzers were
  unavailable. This remains a host model, not a boot-tested OS image.
- No sanitizer, coverage-guided fuzzer, coverage run, benchmark, cross-architecture test, hardware
  test, student-view export, or production validation was performed.
- The local builds, supplied tests, focused cursor probe, and archive audits do not replace the
  required fresh independent review. The pack therefore remains `GENERATED` + `PARTIAL`.
