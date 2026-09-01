# Revision Debugging Log

This log records commands, changes, and observable results without private chain-of-thought.

## 1. Workspace inventory

- Command: `find . -maxdepth 3 -type f -print | sort`
- Observation: the initial writable workspace contained the factory marker, job/input files, feedback, and the read-only prior prose, but no implementation or supporting deliverables.
- Action: reconstructed a complete source submission in the writable root without changing `LEARNER_MATERIAL/`, `PRIOR_ATTEMPT/`, or `EXAMINER_FEEDBACK/`.

## 2. First strict build

- Commands: `make clean`, then `make`
- Result: both exited 0. GCC 8.5.0 compiled all five translation units under `-std=c17 -Wall -Wextra -Wpedantic -O2` without diagnostics.
- Observation: the parser/queue/scheduler/report interfaces linked successfully as separate modules.

## 3. First unattended suite

- Command: `make test`
- Result: exited 0; all 20 named tests passed in 0.619 seconds, including 60 seeded differential subcases.
- Observation: exact hand oracles agreed with both the program and the independent model for the public example, endpoint rule, and idle accounting.

## 4. Safety-tool probes

- Command: `make analyze` while an experimental analyzer target was present.
- Result: exited 2 because GCC 8.5.0 reports `-fanalyzer` as an unrecognized option.
- Action: removed the unsupported convenience target from the final Makefile.
- Command: clean instrumented build using `-fsanitize=address,undefined -fno-omit-frame-pointer` at compile and link time.
- Result: all objects compiled, but the link exited 2 because `/usr/lib64/libasan.so.5.0.0` and `/usr/lib64/libubsan.so.1.0.0` are missing. No sanitizer executable or test run was produced.
- Follow-up: `command -v` found no Valgrind, GDB, Clang, cppcheck, or scan-build.
- Observation: these are tooling limitations, not successful safety validation.

## 5. Final reproducibility run

- Commands: `make clean`, `make`, `make test`
- Results: statuses 0, 0, and 0. The final build emitted no compiler diagnostics; all 20 tests passed in 0.605 seconds.
- Evidence: exact command output and validation labels are preserved in `EVIDENCE.txt`.
- Finalization: generated objects and `rrsim` were removed with `make clean` after evidence capture.
