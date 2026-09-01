# Validation record

This file records local worker observations from 2026-08-31 in the supplied
`America/Chicago` environment. They are not independent validation and do not change the manifest:
the artifact remains `GENERATED` + `PARTIAL`, with independent validation required. In particular,
the benchmark harness smoke run is not a benchmark result, and no `TESTED`, `BENCHMARKED`,
`REVIEWED`, `PRODUCTIONIZED`, or other promotion is claimed.

The command runner prefixed invocations with three identity lookup warnings (`/usr/bin/id: cannot
find name for user ID 532319`, the corresponding group ID `500275`, then the user ID again). These
runner warnings were not emitted by project code.

## Toolchain

Command:

```sh
sh environment/check_toolchain.sh
```

Observed exit status: `0`.

```text
cc: /usr/bin/cc
make: /usr/bin/make
python3: /usr/bin/python3
C compiler: cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
make: GNU Make 4.2.1
python: Python 3.6.8
```

No upstream repository or linked tutorial was accessed.

## Starter boundary

Command:

```sh
make -C starter clean all check
```

Observed exit status: `0`. All three starter translation units compiled with
`-std=c11 -Wall -Wextra -Wpedantic -Werror -g`, linking produced `starter/byosh`, and the final test
line was:

```text
baseline parser contract: PASS
```

The advanced learner target was also run to verify that the starter does not contain the later
solution:

```sh
make -C public_tests clean milestones
```

Observed exit status: `2`. Compilation succeeded, then the test reported exactly
`17 milestone assertion(s) failed`; Make reported an error for target `milestones`. Failures covered
the deliberately unimplemented quote/escape, pipeline/redirection/background, and malformed-syntax
milestones. This is the expected initial learning boundary and one reason `PARTIAL` remains accurate.

## Sealed reference

Clean build command:

```sh
make -C sealed/reference clean all
```

Observed exit status: `0`. GCC compiled `main.c`, `lexer.c`, `parser.c`, `jobs.c`, and `builtins.c`
with `-D_POSIX_C_SOURCE=200809L -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -g`, then linked
`sealed/reference/byosh`.

Test command after the final normal rebuild:

```sh
make -C sealed/reference_tests test SHELL_UNDER_TEST=/projects/se/pj34000401_refsys/users/yuali01/learn/learning-factory/warehouse/workspaces/job_byox_build_v1_f28eb4a989ab40317e251eb03bb7588a/attempt-001/sealed/reference/byosh
```

Observed exit status: `0`.

```text
Ran 32 tests in 2.818s

OK
```

All 32 cases printed `ok`. The run covered parsing, duplicate-redirection atomicity, closed-standard-FD
redirection, long concurrent pipelines, built-in parent/child context, statuses, background jobs,
idle completion collection, and pseudo-terminal stop/`jobs`/`bg`/`fg`/interrupt behavior. No case was
reported as skipped.

Public black-box command:

```sh
make -C public_tests cli SHELL_UNDER_TEST=../sealed/reference/byosh
```

Observed exit status: `0` and final output:

```text
completed-shell public smoke tests: PASS
```

## Exercise and harness checks

The intentionally faulty debugging programs were compiled but not executed. The review candidates
were compiled without linking:

```sh
mkdir .validation-build
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror debugging/exercise_01_pipe_eof/buggy.c -o .validation-build/debug_01
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror debugging/exercise_02_wait_status/buggy.c -o .validation-build/debug_02
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror debugging/exercise_03_sigchld_race/buggy.c -o .validation-build/debug_03
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -c review_exercises/exercise_01_parser_ownership/candidate.c -o .validation-build/review_01.o
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -c review_exercises/exercise_02_terminal_handoff/candidate.c -o .validation-build/review_02.o
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Werror -c review_exercises/exercise_03_builtin_context/candidate.c -o .validation-build/review_03.o
```

Observed exit status for the complete compilation sequence: `0`, with no compiler output.

Python compatibility and bounded harness commands:

```sh
python3 -m py_compile public_tests/test_cli.py sealed/reference_tests/test_shell.py sealed/reference_tests/audit_pack.py benchmarks/run_bench.py
python3 benchmarks/run_bench.py --shell ./sealed/reference/byosh --warmups 0 --iterations 1 >/dev/null
```

Both commands observed exit status `0` and no output. The benchmark JSON was deliberately discarded;
no timings were retained and no benchmark claim is made.

## Informative unavailable diagnostic

Command:

```sh
make -C sealed/reference clean all CFLAGS='-std=c11 -Wall -Wextra -Wpedantic -Werror -g -fno-omit-frame-pointer -fsanitize=address,undefined' LDFLAGS='-fsanitize=address,undefined'
```

Observed exit status: `2`. Instrumented compilation completed, but the linker reported:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
make: *** [Makefile:15: byosh] Error 1
```

Therefore AddressSanitizer/UndefinedBehaviorSanitizer execution was unavailable on this host. The
ordinary clean build and 32-test run recorded above were repeated successfully after this failed
attempt.

## Final pack audit

Command:

```sh
python3 sealed/reference_tests/audit_pack.py
```

Observed exit status: `0`.

```text
pack audit: PASS
required files: 23
forbidden paths: 0
locally sealed exercise answers: 6
symlinks or special files: 0
credential-scanned generated files: 62
manifest labels: GENERATED, PARTIAL
```
