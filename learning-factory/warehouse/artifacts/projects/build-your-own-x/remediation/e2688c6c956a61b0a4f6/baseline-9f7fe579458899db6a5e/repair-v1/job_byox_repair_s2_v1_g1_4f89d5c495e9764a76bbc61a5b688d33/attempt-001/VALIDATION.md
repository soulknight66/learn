# Repair validation evidence

Observed locally on 2026-09-03 in the allocated repair workspace (timezone
America/Chicago). Every result below was rerun against this repaired pack; no
prior-build result is treated as validation evidence. These checks are not
independent validation and do not promote the artifact beyond the `GENERATED`
+ `PARTIAL` labels in `MANIFEST.yaml`.

## Tool identities

Useful configured binaries were invoked by exact path.

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0
exit 0

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/as --version
GNU assembler (GNU Binutils) 2.43
target: x86_64-pc-linux-gnu
exit 0

$ /arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld --version
GNU ld (GNU Binutils) 2.43
exit 0

$ /arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-gcc --version
aarch64-none-elf-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203
exit 0

$ /arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-nm --version
GNU nm (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 2.45.1.20251203
exit 0

$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64 --version
QEMU emulator version 9.1.1
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
exit 0

$ /usr/bin/make --version
GNU Make 4.2.1
exit 0
```

## Pinned hosted assembler and linker

The repaired makefiles pass a `-B` prefix for the configured Binutils
directory. GCC reported the selected programs as follows:

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -print-prog-name=as
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/as
exit 0

$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -print-prog-name=ld
/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ld
exit 0
```

A complete hosted contract executable was then compiled with `PATH` removed;
the configured `-B` prefix supplied both assembler and linker discovery:

```text
$ /usr/bin/env -u PATH /usr/bin/timeout --foreground 30s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Isealed/reference/include sealed/reference/src/process.c sealed/reference/src/vm.c sealed/reference/src/ramfs.c sealed/reference_tests/test_reference.c -o sealed/reference/build/host/reference_tests
exit 0

$ /usr/bin/timeout --foreground 10s sealed/reference/build/host/reference_tests
[PASS] process initialization and errors
[PASS] process lifecycle
[PASS] process capacity and PID exhaustion
[PASS] VM boundaries and permissions
[PASS] VM capacity and aliasing
[PASS] filesystem names and capacity
[PASS] filesystem I/O and atomicity
reference contract tests: 7/7 passed
exit 0
```

The filesystem groups above include byte-for-byte checks of two differently
prefilled `ramfs_t` objects after `fs_init`, and of a whole `fs_file_t` slot
after `fs_unlink`. Thus the checks cover the repaired padding-byte defect, not
only named fields.

## Learner scaffold

```text
$ /usr/bin/timeout --foreground 60s /usr/bin/make -C starter clean compile
[three GCC 15.2.0 C11 compilations, each using -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ and -Wall -Wextra -Werror -pedantic]
exit 0

$ /usr/bin/timeout --foreground 60s /usr/bin/make -C starter test
[PASS] initializers
[FAIL] process round robin
[FAIL] process rejections
[FAIL] virtual memory
[FAIL] RAM filesystem
1/5 public checks passed
make: *** [Makefile:33: test] Error 1
exit 2
```

The exit 2 is the expected TODO scaffold baseline. The initializer group now
compares complete RAMFS object representations and passed; behavior-changing
learner operations remain stubs, so their four groups remain intentionally
failing.

## Clean reference build and execution

```text
$ /usr/bin/timeout --foreground 90s /usr/bin/make -C sealed/reference clean all
[PASS] process initialization and errors
[PASS] process lifecycle
[PASS] process capacity and PID exhaustion
[PASS] VM boundaries and permissions
[PASS] VM capacity and aliasing
[PASS] filesystem names and capacity
[PASS] filesystem I/O and atomicity
reference contract tests: 7/7 passed
[PASS] 4000 deterministic process operations
[PASS] 4000 deterministic VM operations
[PASS] 4000 deterministic filesystem operations
MINIOS: PASS
exit 0
```

The hosted compile lines used GCC 15.2.0 with the configured Binutils `-B`
prefix. The same subsystem sources then compiled freestanding with the exact
AArch64 compiler above. The fresh QEMU UART log contained:

```text
MiniOS freestanding boot
processes: ok
virtual-memory: ok
ramfs: ok
MINIOS: PASS
```

The linked image was also checked for unresolved symbols:

```text
$ /arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-nm -u sealed/reference/build/aarch64/minios.elf
[no output]
exit 0
```

## Sanitizers

The repaired reference and its contract tests were rebuilt with AddressSanitizer
and UndefinedBehaviorSanitizer:

```text
$ /usr/bin/timeout --foreground 30s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -B/arm/tools/gnu/binutils/2.43/rhe8-x86_64/bin/ -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isealed/reference/include sealed/reference/src/process.c sealed/reference/src/vm.c sealed/reference/src/ramfs.c sealed/reference_tests/test_reference.c -o sealed/reference/build/host/reference_tests_sanitized
exit 0

$ /usr/bin/env LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 ASAN_OPTIONS=detect_leaks=0 /usr/bin/timeout --foreground 15s sealed/reference/build/host/reference_tests_sanitized
[all seven groups PASS]
reference contract tests: 7/7 passed
exit 0
```

No ASan or UBSan diagnostic was emitted. Leak detection was disabled because
this workspace does not provide the ptrace behavior LeakSanitizer requires.

## Cleanup

The sanitizer executable was removed with the exact command
`/bin/rm sealed/reference/build/host/reference_tests_sanitized` (exit 0).
Then these bounded cleanup commands each exited 0:

```text
$ /usr/bin/timeout --foreground 30s /usr/bin/make -C starter clean
$ /usr/bin/timeout --foreground 30s /usr/bin/make -C sealed/reference clean
```

They removed only reproducible objects, test executables, the emulator log,
and the ELF image.

## Final structure, metadata, and preservation audit

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/validate_structure.py
structure: PASS (23 required files, no forbidden paths)
archive types: PASS (regular files and directories only)
credential patterns: PASS
metadata status: PASS (GENERATED + PARTIAL)
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool MANIFEST.yaml >/dev/null
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool PROVENANCE.json >/dev/null
exit 0

$ /usr/bin/cmp -s starter/include/minios.h sealed/reference/include/minios.h
exit 0

$ /usr/bin/cmp -s PRIOR_BUILD/MANIFEST.yaml MANIFEST.yaml
exit 0

$ /usr/bin/cmp -s PRIOR_BUILD/PROVENANCE.json PROVENANCE.json
exit 0

$ find starter sealed/reference -type d -name build -print
[no output]
exit 0
```

The exact manifest and immutable provenance files remain byte-identical to the
prior pack. A read-only Python preservation probe enumerated all source files
under `PRIOR_BUILD` and checked that each corresponding output path is a
regular file. Its corrected invocation reported:

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'from pathlib import Path; source=Path("PRIOR_BUILD"); files=[p for p in source.rglob("*") if p.is_file()]; missing=[p.relative_to(source).as_posix() for p in files if not (Path.cwd()/p.relative_to(source)).is_file()]; status="PASS" if not missing else "FAIL"; print("prior-file preservation: {} ({} source files, {} missing)".format(status,len(files),len(missing))); raise SystemExit(bool(missing))'
prior-file preservation: PASS (47 source files, 0 missing)
exit 0
```

The first attempted form of that probe exited 1 with Python's
`SyntaxError: f-string expression part cannot include a backslash`; it did not
execute the filesystem check or indicate an artifact defect. The corrected
command and result above are retained as the actual preservation evidence.

## Honest partial boundary

No physical Raspberry Pi was available or configured, so no board image was
loaded and no board-specific peripheral claim is made. QEMU `virt` is not a
substitute for Raspberry Pi validation. The model also does not install real
page tables, enter user mode, switch register contexts, or persist filesystem
data. No independent fuzzing, benchmarking, production assessment, or learner
transfer validation was performed. Independent validators remain mandatory.
