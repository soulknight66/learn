# Repair validation record

Date: 2026-09-01 (America/Chicago)

Artifact status remains `GENERATED` + `PARTIAL`. All results below were observed in this repair
workspace with bounded commands. They are builder-local evidence only; they do not grant `BUILDS`,
`TESTED`, `TRANSFER_VERIFIED`, `REVIEWED`, `BENCHMARKED`, `FUZZED`, or `PRODUCTIONIZED`.
Independent validation remains required.

The shell printed an infrastructure warning that numeric UID/GID names could not be resolved before
commands. It did not change the reported command exit statuses.

## Host inventory

```text
$ timeout 10s sh environment/check.sh
cc: available
make: available
arm-none-eabi-gcc: unavailable
qemu-system-arm: unavailable
exit 0
```

## Strict host builds and repaired tests

The intentionally incomplete starter and the repaired sealed reference both compiled with the
submitted strict C11 flags:

```text
$ timeout 30s make -C starter clean all
mkdir -p build
cc -Iinclude -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic -c src/kernel.c -o build/kernel.o
ar rcs libtinyarm.a build/kernel.o
exit 0

$ timeout 30s make -C sealed/reference clean all
mkdir -p build
cc -I../../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic -c src/kernel.c -o build/kernel.o
ar rcs libtinyarm-reference.a build/kernel.o
exit 0
```

The public tests passed against the sealed reference. The sealed suite now has a seventh group that
performs the reviewed exit, reap, same-slot replacement, and nested-tick sequence:

```text
$ timeout 30s make -C public_tests clean test IMPL_DIR=../sealed/reference
cc -I../sealed/reference/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic test_public.c ../sealed/reference/src/kernel.c  -o public_tests
./public_tests
public tests: 3 groups passed
exit 0

$ timeout 30s make -C sealed/reference_tests clean test
cc -I../../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic test_reference.c ../reference/src/kernel.c  -o reference_tests
./reference_tests
sealed reference tests: 7 groups passed
exit 0
```

To show that the added group detects the concrete prior defect, the repaired test source was compiled
once against the read-only archived prior implementation. The old implementation failed only the new
identity group at the assertion that PID 2 remains running; the scratch executable was then removed
with `make -C sealed/reference_tests clean`.

```text
$ timeout 30s cc -Istarter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic sealed/reference_tests/test_reference.c PRIOR_BUILD/sealed/reference/src/kernel.c -o sealed/reference_tests/reference_tests
exit 0
$ timeout 20s sealed/reference_tests/reference_tests
FAIL sealed/reference_tests/test_reference.c:175: replacement->state == MK_TASK_RUNNING
1 sealed test group(s) failed
exit 1
```

The starter remains incomplete by design. Its public test executable compiled, then all three groups
failed at the documented initialization stubs:

```text
$ timeout 30s make -C public_tests clean test IMPL_DIR=../starter
cc -I../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic test_public.c ../starter/src/kernel.c  -o public_tests
./public_tests
FAIL test_public.c:49: mk_init(&kernel, 1u) == MK_OK
FAIL test_public.c:69: mk_init(&kernel, 2u) == MK_OK
FAIL test_public.c:88: mk_init(&kernel, 1u) == MK_OK
3 public test group(s) failed
make: *** [Makefile:20: test] Error 1
exit 2
```

## Informative blocked attempts

Sanitizer compilation reached the linker, but the host sanitizer runtimes were absent:

```text
$ timeout 30s make -C sealed/reference_tests clean test SANITIZE=1
cc -I../../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic -O1 -fno-omit-frame-pointer -fsanitize=address,undefined test_reference.c ../reference/src/kernel.c -fsanitize=address,undefined -o reference_tests
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
make: *** [Makefile:16: reference_tests] Error 1
exit 2
```

The optional ARM build stopped at the unavailable cross compiler:

```text
$ timeout 30s make -C sealed/reference/arm clean all
arm-none-eabi-gcc -mcpu=cortex-a15 -marm -ffreestanding -fno-builtin -nostdlib -O2 -ffunction-sections -fdata-sections -Wall -Wextra -Werror start.S context_switch.S kernel_main.c -T linker.ld -nostdlib -Wl,--gc-sections -Wl,--build-id=none -o kernel.elf
make: arm-none-eabi-gcc: Command not found
make: *** [Makefile:13: kernel.elf] Error 127
exit 2
```

QEMU was not attempted because both the cross compiler and emulator were unavailable and no ARM
binary existed. Sanitizer cleanliness, ARM build/boot, fuzzing, benchmarking, learner transfer,
security, and production readiness remain unverified.

## Cleanup and packaging checks

The following bounded clean commands all exited 0, and the subsequent artifact search printed
nothing:

```text
$ timeout 20s make -C starter clean
$ timeout 20s make -C sealed/reference clean
$ timeout 20s make -C public_tests clean
$ timeout 20s make -C sealed/reference_tests clean
$ timeout 20s make -C sealed/reference/arm clean
$ find starter public_tests sealed/reference sealed/reference_tests -type f \( -name '*.o' -o -name '*.a' -o -name 'public_tests' -o -name 'reference_tests' -o -name '*.elf' -o -name '*.bin' \) -print
exit 0; no output
```

A final bounded Python check used the authoritative required and forbidden lists, walked only the
generated pack roots, rejected non-regular/non-directory objects, parsed both metadata documents
with duplicate-key rejection, checked the exact manifest and immutable serialized metadata digests,
and searched every generated regular file for common credential signatures:

```text
$ timeout 20s python3 environment/verify_pack.py
required paths: 23 regular files
forbidden paths: 21 absent
pack objects: 48 regular files, 22 directories, 0 other
manifest: exact required object; status GENERATED; labels GENERATED, PARTIAL
provenance: valid strict JSON; immutable serialized digest matched
credential signature matches: 0
exit 0
```

The credential check covered common private-key banners, AWS/GitHub/Slack token forms, and apparent
password/secret/API-key assignments. It is a bounded signature scan, not a comprehensive secret
audit. `MANIFEST.yaml` and `PROVENANCE.json` SHA-256 values were respectively
`0009c3049301ee75de62cd3f2940fd3d0fac99656a925a24bc08c8dc01feeef9` and
`4e1c553ea5c2d770f1701b6556230f609c1c30f188482c3aa1b60b3979567817`.
