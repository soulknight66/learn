# Debugging Log — Unit 0

This is a factual record of commands, hypotheses, results, and fixes. It does not extend beyond the kickoff unit.

## D1 — File enumeration tool unavailable

- Experiment: invoke `rg --files` to identify the supplied course files.
- Result: the shell reported `rg: command not found`.
- Action: used `find` only to enumerate workspace filenames, then read only `COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`.
- Lesson: tool availability must be checked; the fallback should stay within the same narrow scope.

## D2 — Compiler driver could not find its backend

- Experiment: run the first `make clean all`.
- Failure: `cc: error trying to exec 'cc1': execvp: No such file or directory`; make exited 2 before compiling learner code.
- Hypothesis: the driver was present, but its GCC helper search paths were not discoverable in this runner.
- Experiments: adding the discovered `cc1` directory reached the backend but exposed a missing `stddef.h` search path; adding the GCC library/include directory compiled objects, but linking then reported `cannot find 'ld'`.
- Fix: the Makefile derives GCC target/version and, when the conventional local `cc1` exists, supplies local backend, header, library, assembler, and linker search paths. It does not download a toolchain.
- Retest: ordinary `make clean all` returned 0 with all required warning flags.

## D3 — Contract behavior suite

- Experiment: run `make check` after the toolchain fix.
- Result: all 18 black-box tests passed.
- Covered failures: duplicate maps, a map after access, malformed/signed/out-of-range numbers, malformed permissions, extra tokens, control and non-ASCII bytes, overlong and excess lines, excess accesses, invalid invocation, and missing input files.
- Covered valid boundaries: empty and map-only input, CRLF, an unterminated last line, all modes, both address endpoints, 1,024 accesses, and 256 mappings.

## D4 — Optional sanitizer probe unavailable

- Experiment: build with `CFLAGS='-O1 -g -fsanitize=address,undefined'`.
- Failure: compilation succeeded, but the linker could not access `libasan.so.5.0.0` or `libubsan.so.1.0.0`; make exited 2.
- Action: made no source change based on this environment-only failure and restored the required standard build for final checks.
- Lesson: an unavailable optional runtime is not evidence of a program defect; record the limitation and rely on the required reproducible checks.

## D5 — Final clean reproduction

- Experiment: from the submission root, run `make clean all`, followed by `make check`.
- Result: both commands returned 0; the second run reported all 18 tests passing.
- Evidence: exact commands, versions, statuses, and unedited outputs are recorded under `evidence/` with the `SELF-CHECKED` label only.
