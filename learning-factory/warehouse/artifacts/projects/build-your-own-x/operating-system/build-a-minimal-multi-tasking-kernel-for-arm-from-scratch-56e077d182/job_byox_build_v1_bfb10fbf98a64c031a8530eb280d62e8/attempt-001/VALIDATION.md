# Validation record

Date: 2026-08-31 (America/Chicago)

Artifact status remains `GENERATED` + `PARTIAL`. The observations below are builder-local evidence;
they do not grant `BUILDS`, `TESTED`, `TRANSFER_VERIFIED`, `REVIEWED`, `BENCHMARKED`, `FUZZED`, or
`PRODUCTIONIZED`. Independent validation remains required.

## Host inventory

Commands and observed output:

```text
$ cc --version 2>/dev/null | head -n 1
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)

$ make --version 2>/dev/null | head -n 1
GNU Make 4.2.1

$ sh environment/check.sh
cc: available
make: available
arm-none-eabi-gcc: unavailable
qemu-system-arm: unavailable
```

The login shell also printed an infrastructure warning that numeric UID/GID names could not be
resolved. It did not affect compiler or test execution.

## Builds and host tests

Starter compilation was observed to succeed:

```text
$ make -C starter clean all
cc -Iinclude -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic -c src/kernel.c -o build/kernel.o
ar rcs libtinyarm.a build/kernel.o
```

Sealed reference compilation was observed to succeed:

```text
$ make -C sealed/reference clean all
cc -I../../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic -c src/kernel.c -o build/kernel.o
ar rcs libtinyarm-reference.a build/kernel.o
```

The public suite was compiled against the sealed reference and passed:

```text
$ make -C public_tests clean test IMPL_DIR=../sealed/reference
cc -I../sealed/reference/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic test_public.c ../sealed/reference/src/kernel.c  -o public_tests
./public_tests
public tests: 3 groups passed
```

The expanded sealed suite was compiled against the sealed reference and passed:

```text
$ make -C sealed/reference_tests clean test
cc -I../../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic test_reference.c ../reference/src/kernel.c  -o reference_tests
./reference_tests
sealed reference tests: 6 groups passed
```

The intentionally incomplete learner starter was also run against public tests. Compilation
succeeded and execution failed as designed, preserving a reproducible initial challenge state:

```text
$ make -C public_tests clean test IMPL_DIR=../starter
cc -I../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic test_public.c ../starter/src/kernel.c  -o public_tests
./public_tests
FAIL test_public.c:49: mk_init(&kernel, 1u) == MK_OK
FAIL test_public.c:69: mk_init(&kernel, 2u) == MK_OK
FAIL test_public.c:88: mk_init(&kernel, 1u) == MK_OK
3 public test group(s) failed
make: *** [Makefile:20: test] Error 1
```

## Informative blocked attempts

Sanitizer compilation reached the linker but the host runtimes were missing:

```text
$ make -C sealed/reference_tests clean test SANITIZE=1
cc -I../../starter/include -std=c11 -O2 -g -Wall -Wextra -Werror -pedantic -O1 -fno-omit-frame-pointer -fsanitize=address,undefined test_reference.c ../reference/src/kernel.c -fsanitize=address,undefined -o reference_tests
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
make: *** [Makefile:16: reference_tests] Error 1
```

The ARM build was attempted and failed reproducibly at the unavailable cross compiler:

```text
$ make -C sealed/reference/arm clean all
arm-none-eabi-gcc -mcpu=cortex-a15 -marm -ffreestanding -fno-builtin -nostdlib -O2 -ffunction-sections -fdata-sections -Wall -Wextra -Werror start.S context_switch.S kernel_main.c -T linker.ld -nostdlib -Wl,--gc-sections -Wl,--build-id=none -o kernel.elf
make: arm-none-eabi-gcc: Command not found
make: *** [Makefile:13: kernel.elf] Error 127
```

QEMU execution was not attempted because `qemu-system-arm` was unavailable and there was no ARM
binary. No ARM boot output, sanitizer-clean claim, benchmark, fuzz result, or production claim is
made.

## Packaging checks

After testing, generated libraries, objects, and test executables were explicitly cleaned. A final
local check confirmed that all 23 authoritative required paths were regular files, all forbidden
paths were absent, no symlink or special file existed in generated artifact directories, both JSON
documents parsed, and a credential-signature scan of generated text returned no match. These checks
are packaging observations only and remain subject to the orchestrator's independent validator.
