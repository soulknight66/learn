# Validation evidence

Observed locally on 2026-09-03 in the allocated workspace (timezone
America/Chicago). These observations are not independent validation and do not
promote the artifact beyond the `GENERATED` + `PARTIAL` labels in
`MANIFEST.yaml`.

## Toolchain identification

All useful binaries were invoked by absolute path.

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0
exit 0

$ /arm/tools/arm/arm-gnu-toolchain-aarch64-none-elf/15.2.rel1/linux64/bin/aarch64-none-elf-gcc --version
aarch64-none-elf-gcc (Arm GNU Toolchain 15.2.Rel1 (Build arm-15.86)) 15.2.1 20251203
exit 0

$ /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64 --version
/arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64: symbol lookup error: /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64: undefined symbol: g_date_time_format_iso8601
exit 127

$ env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64 --version
QEMU emulator version 9.1.1
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5
exit 0
```

The failed first QEMU invocation is retained because it identifies a
reproducible host-runtime dependency. Supplying the configured GLib directory
resolved it; the build file scopes that variable to QEMU.

## Learner scaffold

```text
$ cd starter && make clean compile
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Iinclude -c src/process.c -o build/process.o
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Iinclude -c src/vm.c -o build/vm.o
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Iinclude -c src/ramfs.c -o build/ramfs.o
exit 0

$ cd starter && make test
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -std=c11 -O2 -Wall -Wextra -Werror -pedantic -Iinclude src/process.c src/vm.c src/ramfs.c ../public_tests/test_public.c -o build/public_tests
[PASS] initializers
  line 54: expected proc_spawn(&table, 0, (uintptr_t)0x1000u, &first) == OS_OK
[FAIL] process round robin
  line 79: expected proc_spawn(&table, 777u, (uintptr_t)0, &pid) == OS_ERR_NOT_FOUND
[FAIL] process rejections
  line 96: expected vm_map(&space, 0x1000u, 0x5000u, (uint8_t)(VM_READ | VM_WRITE | VM_USER)) == OS_OK
[FAIL] virtual memory
  line 122: expected fs_create(&fs, "/note") == OS_OK
[FAIL] RAM filesystem
1/5 public checks passed
make: *** [Makefile:31: test] Error 1
exit 2
```

That failing run is expected evidence of a progressively revealable starter:
the initializer checkpoint is implemented and all solution-bearing operations
remain TODO stubs. It is not counted as a reference failure or a passing test
claim.

## Clean reference build and execution

Command:

```text
$ cd sealed/reference && make clean all
```

The command rebuilt all hosted and AArch64 objects from source with the exact
compilers above. Observed hosted results:

```text
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
```

The same subsystem sources were then compiled freestanding for Cortex-A53 and
linked without libc. QEMU was invoked as:

```text
env LD_LIBRARY_PATH=/arm/tools/gnu/glib/2.82.1/rhe8-x86_64/lib64 \
  /arm/tools/qemu/qemu/9.1.1/linux64/bin/qemu-system-aarch64 \
  -machine virt -cpu cortex-a53 -smp 1 -m 128M -nographic \
  -monitor none -serial stdio -no-reboot \
  -semihosting-config enable=on,target=native \
  -kernel build/aarch64/minios.elf
```

Observed UART output and process result:

```text
MiniOS freestanding boot
processes: ok
virtual-memory: ok
ramfs: ok
MINIOS: PASS
make clean all: exit 0
```

## Structure, metadata, and credential scan

```text
$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/validate_structure.py
structure: PASS (23 required files, no forbidden paths)
archive types: PASS (regular files and directories only)
credential patterns: PASS
metadata status: PASS (GENERATED + PARTIAL)
exit 0

$ cmp -s starter/include/minios.h sealed/reference/include/minios.h
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool MANIFEST.yaml
exit 0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -m json.tool PROVENANCE.json
exit 0
```

The deterministic scanner checks required and forbidden paths, archive object
types, strict-JSON manifest parsing and exact manifest content, provenance
linkage, and private-key/common-token signatures in generated regular files.

## Honest partial boundary

No physical Raspberry Pi was available or configured, so no board image was
loaded and no board-specific peripheral claim is made. QEMU `virt` is not a
substitute for Raspberry Pi validation. The model also does not install real
page tables, enter user mode, switch register contexts, or persist filesystem
data. No independent fuzzing, benchmark, production, or transfer validation
was performed. Independent validators remain mandatory.

After capturing the transcript, the exact command
`make -C starter clean && make -C sealed/reference clean` exited 0. This
explicitly removed only
scratch objects, test executables, the emulator log, and the ELF image; all
sources and reproducible build recipes remain in the artifact. The structure
and credential scan above was rerun after cleanup and again exited 0.
