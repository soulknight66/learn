# Validation evidence

Generated on 2026-09-03 in the allocated workspace. These are worker-observed results only. They do not constitute independent validation or promote the manifest beyond `GENERATED` + `PARTIAL`.

## Tool identity

Exact commands and observed first lines:

```text
$ /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
gcc (GCC) 15.2.0

$ /arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
Python 3.11.5

$ /usr/bin/make --version
GNU Make 4.2.1
```

The compiler and Python interpreter were invoked from the configured read-only toolchain roots by absolute path. `/usr/bin/make` is a host utility.

## Starter baseline

Command:

```sh
/usr/bin/make -C starter clean all \
  CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
```

Observed: exit 0. All four starter translation units compiled with C17, POSIX feature selection, `-Wall -Wextra -Wpedantic -Werror`, and linked as `starter/minish`.

The deliberately incomplete baseline was also tested:

```sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
MAKE=/usr/bin/make \
public_tests/run.sh starter
```

Observed: exit 1 with `15 public core check(s) failed`. The diagnostics identify the lexing/parsing TODOs. This failure is expected and preserved as evidence that the starter does not contain the solution.

## Reference build and public suite

Command:

```sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
MAKE=/usr/bin/make \
public_tests/run.sh sealed/reference
```

Observed: exit 0. Terminal result lines:

```text
public core tests: PASS
public CLI tests: PASS
```

## Sealed reference suite

Command:

```sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
MAKE=/usr/bin/make \
sealed/reference_tests/run.sh sealed/reference
```

Observed: exit 0. Terminal result lines:

```text
sealed reference unit tests: PASS
sealed CLI tests: PASS
sealed PTY test: PASS
```

The run included a 220-pipeline descriptor-pressure case under `RLIMIT_NOFILE=32` and one real-PTY foreground Ctrl-C case. These finite cases are not proof of race freedom or leak freedom.

## Sanitizer attempt

The sealed unit test was compiled with:

```sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc \
  -std=c17 -D_POSIX_C_SOURCE=200809L \
  -Wall -Wextra -Wpedantic -Werror -O1 -g \
  -fsanitize=address,undefined -fno-omit-frame-pointer \
  -Isealed/reference/include \
  sealed/reference_tests/test_reference.c \
  sealed/reference/src/lexer.c sealed/reference/src/parser.c \
  sealed/reference/src/execute.c \
  -o sealed/reference_tests/.san-build/test_reference
```

Observed compile result: exit 0. The first execution, without a loader path, exited 127 because `libasan.so.8` was not in the default loader search path. With
`LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64`, leak detection then exited 1 because LeakSanitizer reported that it cannot operate under the host's ptrace environment. Both failures are environmental and are retained rather than reported as passes.

The same binary was finally run with leak detection explicitly disabled:

```sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 \
ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 \
UBSAN_OPTIONS=halt_on_error=1 \
sealed/reference_tests/.san-build/test_reference
```

Observed: exit 0 and `sealed reference unit tests: PASS`; no AddressSanitizer or UndefinedBehaviorSanitizer diagnostic was emitted. This is a bounded worker observation, not a `TESTED` or production-readiness label. LeakSanitizer remains unavailable in this host configuration.

## Structural and content audit

Command to be run after build products are cleaned:

```sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 \
  environment/audit_pack.py .
```

The audit checks all 23 required regular files, absence of all 21 forbidden paths, JSON-equivalent immutable metadata, absence of symlinks/special files, and generated text against high-signal private-key/token/credential-assignment patterns.

Observed after `make clean` and removal of test scratch directories: exit 0 with:

```text
pack audit: PASS (23 required files, 21 forbidden paths absent, 50 text files scanned)
```

## Explicit limits

- No upstream resource was fetched or inspected.
- No benchmark was run and no performance number is claimed.
- No fuzzing campaign, coverage target, transfer test, or production review by an independent party occurred.
- Interactive testing covers one PTY scenario; stopped-job selection is not implemented.
- Independent validators, not this document, control `BUILDS`, `TESTED`, `FUZZED`, `BENCHMARKED`, `REVIEWED`, `TRANSFER_VERIFIED`, and `PRODUCTIONIZED` labels.
