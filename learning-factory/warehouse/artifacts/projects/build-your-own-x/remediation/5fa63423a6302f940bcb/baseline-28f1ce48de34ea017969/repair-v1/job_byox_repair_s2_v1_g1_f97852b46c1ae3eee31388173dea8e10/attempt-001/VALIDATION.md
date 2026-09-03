# Validation evidence

Generated on 2026-09-03 in the allocated repair workspace. Every outcome below was observed during repair generation 1; archived prior results were used only to select repairs. These worker observations do not constitute independent validation or promote the manifest beyond GENERATED + PARTIAL.

## Repair scope

The repaired reference:

- retains a descriptor when its source already equals the target standard descriptor;
- closes the unused next-pipe read end before installing pipeline endpoints;
- gives each owned descriptor at most one close call and does not retry close after EINTR; and
- explicitly destroys token and pipeline outputs on lexer/parser failures in both the starter and reference loops.

The sealed suite now includes direct input redirection with fd 0 initially closed, a two-stage pipeline plus output redirection with fd 0 and fd 1 initially closed, and a normal executable-level output-redirection case with inherited fd 1 closed.

## Tool identity

Exact commands:

~~~sh
/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc --version
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 --version
/usr/bin/make --version
/usr/bin/timeout --version
~~~

Observed first lines:

~~~text
gcc (GCC) 15.2.0
Python 3.11.5
GNU Make 4.2.1
timeout (GNU coreutils) 8.30
~~~

GCC and Python were invoked by absolute path from configured read-only toolchain roots. Make and timeout were host utilities.

## Starter baseline

Exact build command:

~~~sh
/usr/bin/timeout --signal=KILL 30s /usr/bin/make -C starter clean all CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc
~~~

Observed: exit 0. All four translation units compiled and linked with the Makefile's C17, POSIX feature, strict warning, and errors-on-warning flags.

Exact public-suite command:

~~~sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 MAKE=/usr/bin/make /usr/bin/timeout --signal=KILL 30s public_tests/run.sh starter
~~~

Observed: exit 1 with 15 public core checks failed. This is the documented deliberately incomplete starter, not a passing implementation. The cleanup repair does not fill any learner TODO.

## Reference public and sealed suites

Exact public-suite command:

~~~sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 MAKE=/usr/bin/make /usr/bin/timeout --signal=KILL 45s public_tests/run.sh sealed/reference
~~~

Observed: exit 0.

~~~text
public core tests: PASS
public CLI tests: PASS
~~~

Exact sealed-suite command:

~~~sh
CC=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc PYTHON=/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 MAKE=/usr/bin/make /usr/bin/timeout --signal=KILL 60s sealed/reference_tests/run.sh sealed/reference
~~~

Observed: exit 0.

~~~text
sealed reference unit tests: PASS
sealed CLI tests: PASS
sealed PTY test: PASS
~~~

This finite suite includes the new initially closed fd 0/fd 1 regressions, a 220-pipeline run under RLIMIT_NOFILE=32, process-group checks, and one PTY Ctrl-C path. It is not proof over all descriptor states or scheduling races.

## Focused closed-stdout reproduction

After the reference build, the prior review's failing shape was rerun through the normal minish executable. Exact command:

~~~sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 -c 'import os,pathlib,subprocess,tempfile; b=pathlib.Path("sealed/reference/minish").resolve(); d=tempfile.TemporaryDirectory(prefix="repair-fd-edge-"); target=pathlib.Path(d.name)/"out"; r=subprocess.run([str(b)],input=f"/usr/bin/printf payload > {target}\n",text=True,stdout=None,stderr=subprocess.PIPE,timeout=5,check=False,preexec_fn=lambda: os.close(1)); print(f"closed-stdout redirection: exit={r.returncode}, size={target.stat().st_size}, content={target.read_text()!r}, stderr={r.stderr!r}"); d.cleanup()'
~~~

Observed: exit 0 from the probe.

~~~text
closed-stdout redirection: exit=0, size=7, content='payload', stderr=''
~~~

## Focused static analysis

Exact command:

~~~sh
/usr/bin/timeout --signal=KILL 30s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -std=c17 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -fanalyzer -Werror=analyzer-fd-double-close -Wno-analyzer-fd-leak -O0 -g -Isealed/reference/include sealed/reference/src/main.c sealed/reference/src/lexer.c sealed/reference/src/parser.c sealed/reference/src/execute.c -o sealed/reference/.analyzed-minish
~~~

Observed: exit 0 with no analyzer diagnostic. In particular, the prior analyzer-fd-double-close finding from retrying close after EINTR was not emitted.

## AddressSanitizer and UndefinedBehaviorSanitizer

Exact compile command:

~~~sh
mkdir -p sealed/reference_tests/.san-build
/usr/bin/timeout --signal=KILL 30s /arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/bin/gcc -std=c17 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Isealed/reference/include sealed/reference_tests/test_reference.c sealed/reference/src/lexer.c sealed/reference/src/parser.c sealed/reference/src/execute.c -o sealed/reference_tests/.san-build/test_reference
~~~

Observed compile result: exit 0.

Exact execution command:

~~~sh
LD_LIBRARY_PATH=/arm/tools/gnu/gcc/15.2.0/rhe8-x86_64/lib64 ASAN_OPTIONS=detect_leaks=0:halt_on_error=1 UBSAN_OPTIONS=halt_on_error=1 /usr/bin/timeout --signal=KILL 30s sealed/reference_tests/.san-build/test_reference
~~~

Observed: exit 0 with sealed reference unit tests: PASS and no AddressSanitizer or UndefinedBehaviorSanitizer diagnostic. Leak detection was explicitly disabled and is not claimed.

## Cleanup and structural audit

Build and analysis products were removed with the Makefile clean targets plus explicit unlink/rmdir operations. The repaired output contains 50 regular source/documentation/test files and no retained executable, object, analyzer, sanitizer, or test-build product.

Exact audit command:

~~~sh
/arm/tools/python/python/3.11.5/rhe8-x86_64/bin/python3 environment/audit_pack.py .
~~~

Observed: exit 0.

~~~text
pack audit: PASS (23 required files, 21 forbidden paths absent, 103 text files scanned)
~~~

The 103 scan count includes the 50 repaired files plus the immutable PRIOR_BUILD and PRIOR_REVIEW staging files present in this repair workspace. Thus every generated text file was included in the credential-pattern scan. The audit also parsed MANIFEST.yaml and PROVENANCE.json as strict JSON and checked them against their immutable expected objects.

Exact generated-output checks excluded only the two staged prior roots and factory-owned dot directories:

~~~sh
find . -path './PRIOR_BUILD' -prune -o -path './PRIOR_REVIEW' -prune -o -path './.factory-workspace' -prune -o -path './.codex' -prune -o -path './.agents' -prune -o ! -type d ! -type f -print
find . -path './PRIOR_BUILD' -prune -o -path './PRIOR_REVIEW' -prune -o -path './.factory-workspace' -prune -o -path './.codex' -prune -o -path './.agents' -prune -o -type f -print | sort | wc -l
find . -path './PRIOR_BUILD' -prune -o -path './PRIOR_REVIEW' -prune -o -path './.factory-workspace' -prune -o -path './.codex' -prune -o -path './.agents' -prune -o -type f \( -name '*.o' -o -name minish -o -name test_reference -o -name .analyzed-minish \) -print
~~~

Observed: the non-regular-object and build-product searches printed no paths; the file count was 50.

## Explicit limits and label discipline

- No upstream resource was fetched or inspected.
- No benchmark, fuzzing campaign, coverage threshold, transfer test, deterministic allocation/syscall fault injection, broad PTY matrix, or long-duration race campaign occurred.
- LeakSanitizer was not validated in this repair run.
- Publication-view filtering remains an orchestrator responsibility; separation was checked structurally.
- Nothing here assigns BUILDS, TESTED, FUZZED, BENCHMARKED, REVIEWED, TRANSFER_VERIFIED, or PRODUCTIONIZED. Fresh independent validation remains required.

