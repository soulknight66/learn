# Revision debugging log

This is a command-and-observation record, not private reasoning.

## 1. Inventory and diagnosis

Command: find . -type f -print | sort

Observation: the starting workspace had the factory marker, JOB.md, three learner-material files, examiner feedback, and three prior-attempt prose files. It did not contain the C implementation, Makefile, tests, design/test documents, evidence, or comprehension responses named by the prior prose.

Action: created new artifacts only in the writable workspace root and tests directory. The three input directories were not modified.

## 2. Implementation and first build

Command: make clean && make

Result: status 0. GCC 8.5.0 compiled main.c, parser.c, queue.c, scheduler.c, and report.c with -std=c17 -Wall -Wextra -Wpedantic -O2 and linked rrsim without a compiler diagnostic.

Observation: parser ownership, FIFO mechanics, event policy, and reporting linked through separate interfaces.

## 3. First unattended test run

Command: make test

Result: status 0; all 22 named tests passed in 0.818 seconds.

Observations:

- The public example matched every required output field and six dispatches.
- The endpoint discriminator required B to run at t=1 ahead of requeued A.
- Late malformed input, cap failures, and command errors all had empty stdout.
- Forty seeded valid workloads matched the suite's separate event model.

## 4. Tool and diagnostic experiments

Command: make clean && make with CFLAGS adding -fsanitize=address,undefined -fno-omit-frame-pointer and matching LDFLAGS.

Result: status 2. All five instrumented objects compiled, but linking failed because /usr/lib64/libasan.so.5.0.0 and /usr/lib64/libubsan.so.1.0.0 were missing. No instrumented executable existed, so no sanitizer test ran.

Commands: command -v valgrind, gdb, clang, cppcheck

Result: none of those tools was available.

Command: make clean && make with additional -Wconversion -Wshadow, followed by make test.

Result: build status 0 with no diagnostics; test status 0 with 22 tests passing in 0.976 seconds.

## 5. Final default in-workspace validation

Commands: make clean; make; make test

Results: statuses 0, 0, and 0. The build used the required default C17 warning flags without diagnostics. All 22 tests passed in 0.850 seconds. Exact command-specific output and validation labels are in EVIDENCE.txt.

## 6. Fresh-directory package reproduction

Commands: archive exactly the MANIFEST.txt paths, extract them beneath .fresh-check/unpacked, verify every listed path with test -f, then run make clean, make, and make test from the extracted directory.

Results: manifest verification status 0; build statuses 0 and 0; test status 0. All 22 tests passed in 1.012 seconds in the extracted copy. This demonstrates that the source, headers, test suite, and documents needed for reproduction were in the package rather than supplied by the original workspace.

Action: removed the explicit .fresh-check scratch tree after recording the result, then ran make clean in the submission root so generated objects and rrsim would not be submitted.
