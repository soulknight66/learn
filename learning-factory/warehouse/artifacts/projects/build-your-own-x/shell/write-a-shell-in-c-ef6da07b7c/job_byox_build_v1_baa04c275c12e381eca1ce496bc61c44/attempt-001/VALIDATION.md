# Validation record

Date: 2026-08-31 (America/Chicago)

This is a record of commands actually run in the allocated workspace. The immutable status remains `GENERATED` + `PARTIAL`: these observations came from the generating worker, not an independent validator, and therefore award no build, test, fuzz, benchmark, review, transfer, or production label.

The linked tutorial was not fetched. No upstream code or prose was used as a build dependency.

## Observed host

Command:

```sh
sh environment/probe.sh
```

Exit status: 0. Observed output:

```text
cc         FOUND
make       FOUND
python3    FOUND
printf     FOUND
true       FOUND
false      FOUND
tr         FOUND
seq        FOUND
wc         FOUND
pwd        FOUND
cat        FOUND
sleep      FOUND
cc (GCC) 8.5.0 20210514 (Red Hat 8.5.0-22)
Python 3.6.8
```

The first public-runner attempt used a feature newer than this observed Python and failed at import with `SyntaxError: future feature annotations is not defined`. The runner was made Python 3.6-compatible and the documented stage selector was changed from newer `unittest -k` behavior to `--stage`.

## Strict builds and public behavior

Commands:

```sh
make -C starter clean all
make -C sealed/reference clean all
python3 public_tests/test_shell.py --shell sealed/reference/msh-reference -v
python3 public_tests/test_shell.py --shell starter/msh --stage invocation -v
```

All four commands exited 0 in the final run. Both C builds used:

```text
-D_POSIX_C_SOURCE=200809L -std=c11 -O2 -g -Wall -Wextra -Wpedantic -Werror
```

Observed test summaries:

```text
Ran 15 tests in 0.299s
OK

Ran 2 tests in 0.006s
OK
```

The two starter checks cover only its intentionally supplied invocation baseline. The incomplete starter is expected to fail later behavioral stages.

## Sealed reference tests

Prerequisite and command:

```sh
make -C sealed/reference clean all
make -C sealed/reference_tests clean test
```

Final exit status: 0. Observed component results:

```text
parser_tests: 6 cases passed
jobs_tests: 3 cases passed
Ran 11 tests in 0.173s
OK
Ran 4 tests in 0.030s
OK
Ran 1 test in 0.161s
OK
```

The 11-test group is noninteractive integration coverage, the 4-test group is bounded adversarial coverage, and the 1-test group uses a pseudo-terminal to send Ctrl-C to a foreground job and verify shell recovery.

An earlier job-test attempt found `tmpfile()` returned null under the sandbox identity (`CHECK failed ... capture != NULL`). The test now uses POSIX `open_memstream`, and the final result above is the observed rerun.

## Debugging and review artifacts

Commands:

```sh
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -o debugging/pipe-eof/broken-demo debugging/pipe-eof/broken.c
timeout 1 debugging/pipe-eof/broken-demo
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -o debugging/pipe-eof/fixed-demo debugging/pipe-eof/sealed/fixed.c
debugging/pipe-eof/fixed-demo
cc -std=c11 -D_POSIX_C_SOURCE=200809L -Wall -Wextra -Wpedantic -Werror -c -o review_exercises/child-boundary/candidate.o review_exercises/child-boundary/candidate.c
```

Observed: both exercise programs printed `payload`; the intentionally broken program timed out with status 124, the sealed fixed program returned 0, and the review candidate compiled successfully. Compilation success is not a correctness claim for the intentionally flawed review candidate.

## Sanitizer attempt — unavailable dependency

Command attempted:

```sh
make -C sealed/reference clean all \
  CFLAGS='-std=c11 -O1 -g -Wall -Wextra -Wpedantic -Werror -fsanitize=address,undefined -fno-omit-frame-pointer' \
  LDFLAGS='-fsanitize=address,undefined'
```

Exit status: 2. Compilation completed, but linking failed with the exact blockers:

```text
/usr/bin/ld: cannot find /usr/lib64/libasan.so.5.0.0
/usr/bin/ld: cannot find /usr/lib64/libubsan.so.1.0.0
collect2: error: ld returned 1 exit status
```

Downstream sanitizer commands could not run because no instrumented binary was produced; their binary-not-found errors are not counted as test results. A normal strict build and the full non-sanitized suite were rerun successfully afterward. Sanitizer validation remains unavailable on this host.

## Structure, metadata, and leakage audit

Command:

```sh
python3 sealed/reference_tests/audit_pack.py
```

Final exit status: 0. Observed output after scratch cleanup:

```text
required paths: present
forbidden paths: absent
filesystem objects: regular files and directories only
manifest: exact expected object
provenance: JSON and binding fields verified
credential signatures: none detected
AUDIT OK
```

The audit scopes content reads to generated artifact roots. It requires every authoritative path, rejects every forbidden path, rejects generated symlinks and special files, compares the strict-JSON manifest to the exact expected object, validates provenance binding fields, and scans readable generated files for private-key headers, access-key forms, and credential assignments.

Scratch executables, objects, reference-test binaries, and the test runner's bytecode cache were removed after recording results. They are reproducible from the retained sources and Makefiles.

## Not run or not claimed

- No benchmark command was run and no benchmark number is recorded.
- No coverage percentage, profiler output, randomized fuzzer result, cross-platform result, or production-readiness result is claimed.
- ASan/UBSan could not link, as recorded above.
- Independent factory validation remains mandatory.
