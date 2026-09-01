# Bounded kickoff-unit submission

## Outcome

Implemented the requested first-unit `proc-run` supervisor and its local
integration suite. This handoff is limited to the manager-authored kickoff
packet; it makes no whole-course or Stanford-completion claim.

## Artifact inventory

- `submission/src/proc_run.cpp`: C++17 implementation.
- `submission/tests/test_proc_run.py`: nine deterministic integration tests.
- `submission/Makefile`: warning-clean build and noninteractive test targets.
- `submission/DESIGN.md`: state transitions, lifecycle invariants, descriptor
  ownership, failure points, and boundary rationale.
- `submission/COMPREHENSION_RESPONSES.md`: ten responses grounded in the
  implementation and tests.
- `submission/README.md`: platform, commands, interface, status contract,
  diagnostic observation, and known limitations.
- `notes.md`: bounded learner notes with hypotheses, experiments, and lessons.
- `debugging-log.md`: reproducible failures, fixes, and validation evidence.

## Provenance

All authored content derives from the three provided learner-safe kickoff files
and experiments run against this implementation in the supplied workspace. No
network content, external solutions, sealed references, factory state, rubrics,
or other student work were used.

## Validation labels

| Label | Evidence |
|---|---|
| **BUILD — PASS** | `make -C submission clean all`; C++17 compilation completed with `-Wall -Wextra -Wpedantic -Werror`. |
| **INTEGRATION — PASS** | `make -C submission test`; 9 tests passed, including 20 repeated quick child runs. |
| **FAILURE PATH — PASS (coverage evidence)** | GCC `--coverage` run of nonexistent executable returned 127; `gcov` observed the parent reap, complete error-report branch, and 127 selection. |
| **SYSCALL TRACE — CONSTRAINED** | `strace` was denied by sandbox `ptrace` policy; `perf trace` lacked tracefs. No successful syscall trace is claimed. |
| **SCOPE — KICKOFF ONLY** | Threads, synchronization, filesystems, networking, distributed systems, and later units were not attempted. |

Build products under `submission/build/` are reproducible from the documented
commands. The source documentation states known limitations rather than
promoting them to supported behavior.
