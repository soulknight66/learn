# Validation record

Date: 2026-08-31 (America/Chicago). All commands were run from the repository root. These are local
observations, not independent validation labels. Manifest status remains `GENERATED` + `PARTIAL`.

## Host inventory

```text
$ gcc -dumpfullversion
8.5.0
exit 0

$ ld -v
GNU ld version 2.30-123.el8
exit 0

$ python3 --version
Python 3.6.8
exit 0
```

```text
$ sh environment/check_tools.sh
required: gcc: found
required: make: found
required: ld: found
required: readelf: found
required: python3: found
optional: qemu-system-i386: unavailable
optional: grub-file: unavailable
optional: grub-mkrescue: unavailable
optional: xorriso: unavailable
exit 0
```

## Supported passing observations

The reference host suite was built from source with strict warnings and run:

```text
$ make -C sealed/reference_tests run
gcc -I../reference/include -I. -std=c11 -Wall -Wextra -Werror -pedantic -O2 test_main.c test_terminal.c test_keyboard.c ../reference/src/terminal.c ../reference/src/keyboard.c -o .build/reference_tests
./.build/reference_tests
reference tests: PASS (532 checks)
exit 0
```

The learner-visible suite was separately compiled against the sealed reference:

```text
$ make -C public_tests PROJECT=../sealed/reference run
gcc -I../sealed/reference/include -I. -std=c11 -Wall -Wextra -Werror -pedantic -O2 test_main.c test_terminal_public.c test_keyboard_public.c ../sealed/reference/src/terminal.c ../sealed/reference/src/keyboard.c -o .build/reference/public_tests
./.build/reference/public_tests
public tests: PASS
exit 0
```

The fixed-seed adversarial harness was compiled and run. This is a deterministic stress test, not a
coverage-guided fuzzing claim:

```text
$ make -C sealed/adversarial run
gcc -I../reference/include -std=c11 -Wall -Wextra -Werror -pedantic -O2 test_stress.c ../reference/src/terminal.c ../reference/src/keyboard.c -o .build/test_stress
./.build/test_stress
adversarial stress: PASS (2209848 invariant checks)
exit 0
```

The freestanding reference was rebuilt from clean objects. Each `.S` file was compiled with
`gcc -m32 -ffreestanding -fno-pie -fno-pic`; each C file was compiled with the Makefile's C11,
freestanding, no-PIE, no-stack-protector, no-builtin, warnings-as-errors flags. The final observed link
line and result were:

```text
$ make -C sealed/reference kernel
ld -m elf_i386 -T arch/i386/linker.ld --build-id=none -o build/kernel.elf build/boot.o build/interrupt_stubs.o build/kernel.o build/terminal.o build/keyboard.o build/interrupts.o
exit 0

$ python3 environment/verify_kernel.py sealed/reference/build/kernel.elf
kernel verification: PASS (ELF32 i386, valid Multiboot-v1 header at file offset 4096)
exit 0

$ readelf -h sealed/reference/build/kernel.elf
Class:                             ELF32
Data:                              2's complement, little endian
Type:                              EXEC (Executable file)
Machine:                           Intel 80386
Entry point address:               0x101000
exit 0

$ readelf -r sealed/reference/build/kernel.elf
There are no relocations in this file.
exit 0

$ nm -u sealed/reference/build/kernel.elf
(no output)
exit 0
```

The sealed polling alternative and focused idle-loop sketch also compile as freestanding i386
objects:

```text
$ gcc -std=c11 -m32 -ffreestanding -fno-pie -Wall -Wextra -Werror -Isealed/reference/include -c sealed/alternatives/polling_input.c -o sealed/alternatives/.build/polling_input.o
(no output)
exit 0

$ gcc -std=c11 -m32 -ffreestanding -fno-pie -Wall -Wextra -Werror -Isealed/reference/include -c sealed/production/event_loop.c -o sealed/production/.build/event_loop.o
(no output)
exit 0
```

## Starter observations

The incomplete starter intentionally compiles and links so learners can work in small increments:

```text
$ make -C starter kernel
ld -m elf_i386 -T arch/i386/linker.ld --build-id=none -o build/kernel.elf build/boot.o build/interrupt_stubs.o build/kernel.o build/terminal.o build/keyboard.o build/interrupts.o
exit 0

$ python3 environment/verify_kernel.py starter/build/kernel.elf
kernel verification: PASS (ELF32 i386, valid Multiboot-v1 header at file offset 4096)
exit 0
```

Its TODOs are genuine. A clean public run compiled successfully, then failed as expected:

```text
$ make -C starter test
public tests: 76 failure(s)
make[1]: *** [Makefile:18: run] Error 1
make: *** [Makefile:34: test] Error 2
exit 2
```

This expected failure is not a reference failure and is not hidden by the build target.

## Blocked and corrected attempts

The optional sanitizer target could compile but could not link because this host lacks its runtime
libraries. The failed target remains reproducible:

```text
$ make -C sealed/reference_tests sanitize
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
make: *** [Makefile:22: .build/reference_tests_sanitize] Error 1
exit 2
```

The first verifier revision used `from __future__ import annotations`, unavailable in Python 3.6.8:

```text
$ python3 environment/verify_kernel.py sealed/reference/build/kernel.elf
File "environment/verify_kernel.py", line 4
  from __future__ import annotations
  ^
SyntaxError: future feature annotations is not defined
exit 1
```

That import was removed; the final verifier pass is recorded above.

No QEMU/GRUB/ISO tool was available, so no kernel was booted, no keyboard IRQ was injected, and no
screen was visually inspected. No benchmark, profiler, physical-hardware, portability, security,
transfer, or production-readiness result exists. Independent validators remain mandatory.

## Packaging audit

The repository-owned audit avoids factory hidden paths and checks the authoritative path lists,
strict JSON objects, generated file types, and common credential shapes:

```text
$ python3 environment/audit_artifact.py
required regular files: 23/23
forbidden paths present: 0
manifest exact object: True
provenance exact canonical object: True
symlinks in generated scope: 0
credential-shaped matches in generated text: 0
artifact audit: PASS
exit 0
```
