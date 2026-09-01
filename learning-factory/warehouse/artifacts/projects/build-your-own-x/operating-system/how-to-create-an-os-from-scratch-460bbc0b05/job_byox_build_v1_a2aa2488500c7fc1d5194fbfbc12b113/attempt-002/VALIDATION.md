# Validation record

Date: 2026-08-31 (America/Chicago)

This is worker-local evidence, not independent validation. The authoritative status remains
`GENERATED` with labels `GENERATED` and `PARTIAL`. No `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`,
`REVIEWED`, `TRANSFER_VERIFIED`, or `PRODUCTIONIZED` label is claimed.

## Tool availability

Command, run from the repository root:

```sh
for tool in cc gcc make ar ld objcopy qemu-system-i386 qemu-system-x86_64 nasm; do command -v "$tool" || echo "$tool: unavailable"; done
cc --version | sed -n '1p'
make --version | sed -n '1p'
```

Observed exit code: `0`.

```text
/usr/bin/cc
/usr/bin/gcc
/usr/bin/make
/usr/bin/ar
/usr/bin/ld
/usr/bin/objcopy
qemu-system-i386: unavailable
qemu-system-x86_64: unavailable
nasm: unavailable
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
GNU Make 4.2.1
```

Consequently, the C model was built and host-tested. No boot, emulator, NASM, hardware, or
architecture-transfer result is available.

## Informative compiler-environment failure

The first clean build was deliberately recorded rather than hidden. Command in a non-login shell:

```sh
make -C starter clean build
```

Observed exit code: `2`.

```text
make: Entering directory '/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_v1_a2aa2488500c7fc1d5194fbfbc12b113/attempt-002/starter'
rm -rf build
mkdir -p build
cc -Iinclude -std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding -c src/scheduler.c -o build/scheduler.o
cc: error trying to exec 'cc1': execvp: No such file or directory
make: Leaving directory '/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_v1_a2aa2488500c7fc1d5194fbfbc12b113/attempt-002/starter'
make: *** [Makefile:23: build/scheduler.o] Error 1
```

The same host's configured login environment resolves GCC's internal executable. Command:

```sh
cc -print-prog-name=cc1
cc -print-search-dirs | sed -n '1,3p'
make -C starter clean build
```

Observed exit code: `0`. The compiler reported
`/usr/libexec/gcc/x86_64-redhat-linux/8/cc1`, then compiled all three objects with
`-std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding` and archived
`starter/build/libmicaos.a`. Configured login-shell commands also emitted three harmless workspace
identity diagnostics because the numeric user/group has no local name; those diagnostics did not
come from the project.

## Deliberately incomplete starter baseline

Command in the configured environment:

```sh
make -C starter test
```

Observed exit code: `2`, expected for the supplied TODO starter.

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

This failure is part of the progressively revealable challenge, not a claim that the starter is a
finished solution.

## Sealed reference build and tests

Command in the configured environment:

```sh
make -C sealed/reference clean test
```

Observed exit code: `0`.

```text
rm -rf -- build
cmp include/micaos.h ../../starter/include/micaos.h
mkdir -p build
cc -Iinclude -std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding -c scheduler.c -o build/scheduler.o
cc -Iinclude -std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding -c vm.c -o build/vm.o
cc -Iinclude -std=c11 -Wall -Wextra -Werror -pedantic -ffreestanding -c ramfs.c -o build/ramfs.o
ar rcs build/libmicaos.a build/scheduler.o build/vm.o build/ramfs.o
cc -Iinclude -std=c11 -Wall -Wextra -Werror -pedantic ../reference_tests/test_reference.c build/libmicaos.a -o build/test_reference
./build/test_reference
reference tests: PASS
```

The header comparison was part of this target and passed.

## Public suite against the sealed implementation

Commands:

```sh
cc -Isealed/reference/include -std=c11 -Wall -Wextra -Werror -pedantic public_tests/test_public.c sealed/reference/build/libmicaos.a -o sealed/reference/build/test_public_against_reference
sealed/reference/build/test_public_against_reference
```

Observed exit code: `0`.

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

## Freestanding archive dependency check

Command:

```sh
nm -u sealed/reference/build/libmicaos.a
```

Observed exit code: `0` and no undefined symbols:

```text
scheduler.o:

vm.o:

ramfs.o:
```

## Scratch cleanup

Commands:

```sh
make -C starter clean
make -C sealed/reference clean
```

Observed exit code: `0`. Both commands removed their explicit `build/` directory, and the final
archive contains source and documentation rather than host-specific object files or executables.

## Final deterministic archive audit

An inline Python 3 audit used the authoritative 23-path required list and 21-path forbidden list,
`lstat` file-type checks, a duplicate-key/NaN-rejecting JSON loader, the exact required manifest
object, provenance cross-field assertions, and a byte comparison of the two public headers. Observed
exit code: `0`.

```text
required regular files: 23/23
forbidden paths present: 0
symlinks or special generated entries: 0
MANIFEST.yaml: strict JSON and exact expected object
PROVENANCE.json: strict JSON; immutable IDs, digest, commit, and license boundary consistent
starter/reference headers: byte-identical
```

A separate targeted scan covered AWS-, GitHub-, and OpenAI-shaped tokens, PEM private-key headers,
and assigned password/API-key/token/secret values in every generated regular file. Observed exit code:
`0`.

```text
credential-pattern scan: 0 matches across 42 generated regular files
```

## Scope and remaining blockers

- QEMU and NASM were unavailable, and the project intentionally supplies no boot image. It remains a
  host-tested model of kernel mechanisms.
- No sanitizer, static analyzer, fuzzer, coverage run, benchmark, cross-compiler, or hardware test was
  performed.
- Local passing reference tests are not validator-controlled evidence. Independent validation remains
  mandatory.
