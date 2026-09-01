# Unit 1 Revision Notes

## Scope

This revision addresses only the self-contained deterministic round-robin simulator kickoff. It does not claim completion of CS162, later units, course credit, or transfer verification.

## What changed after the prior attempt

The independent feedback found that the earlier prose named an implementation and evidence that were not actually present in the submitted workspace. I treated that as an artifact-integrity failure: this revision includes the source, headers, Makefile, executable tests, design/test documentation, evidence, and all comprehension responses alongside fresh learner records. The read-only prior attempt was not modified.

The implementation is newly reconstructable from the public contract:

- `load_tasks` validates the complete file and transfers ownership only on success.
- Task reporting order stays separate from a stable `(arrival, input order)` event order.
- `run_round_robin` admits all arrivals through a slice endpoint before requeueing an unfinished runner.
- A bounded circular queue provides constant-time FIFO operations.
- Event jumps account for idle time without tick simulation.
- Runtime boundary checks reconcile states, remaining service, queue membership, and completed counts.
- Normal output starts only after parsing and scheduling have both succeeded.

## Concrete experiments and observations

1. A strict clean build with `-std=c17 -Wall -Wextra -Wpedantic -O2` exited 0 without compiler diagnostics.
2. `make test` exited 0: 20 named black-box tests passed. The suite includes exact hand oracles for the public example, the two-task endpoint discriminator, and idle gaps, plus 60 reproducible workloads compared with a separate event model.
3. The endpoint workload `A 0 2`, `B 1 1`, quantum 1 produced B first-run 1 and completion 2. This makes the endpoint-before-requeue rule observable.
4. A valid first line followed by `Bad 2x 1` produced nonzero status, a stderr diagnostic, and zero stdout bytes in `test_late_malformed_line_cannot_emit_partial_output`.
5. Exact 128-task and 10,000,000-service workloads passed; the next task/service unit failed with empty stdout.
6. An ASan/UBSan build was attempted. Compilation completed, but linking exited 2 because `libasan.so.5.0.0` and `libubsan.so.1.0.0` are absent. Valgrind, GDB, Clang, cppcheck, and scan-build were also unavailable. No dynamic memory-safety result is claimed.

## Retained lessons

Executable artifacts are part of the result, not something prose can stand in for. Evidence also needs explicit labels: a passing contract suite is a functional validation result, while a failed sanitizer link is only a tooling limitation. Small hand-derived boundary tests and broader differential tests serve different purposes, so this revision retains both.
