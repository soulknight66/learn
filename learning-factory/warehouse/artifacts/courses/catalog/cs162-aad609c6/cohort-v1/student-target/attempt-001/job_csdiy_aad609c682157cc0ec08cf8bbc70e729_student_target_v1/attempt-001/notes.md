# Unit 1 Study Notes

## Boundary and readiness

This work is limited to the self-contained CS162 prerequisite kickoff, Unit 1. It is not an attempt at later CS162 material or course credit. I was already comfortable with C structs, pointers, allocation, separate compilation, queues, asymptotic analysis, compiler diagnostics, and basic debugger use. The practice gap I targeted was production discipline: translating every edge in a prose contract into an interface, cleanup path, and observable test.

## Contract distilled before implementation

- Parse and validate the complete workload before emitting output.
- Preserve original task order for reporting, but build a stable `(arrival, input order)` event order for scheduling.
- At a slice-ending boundary: admit exact-time arrivals, then requeue an unfinished runner, then dispatch.
- A queue removal is a dispatch even if the task completes before one full quantum.
- Jump across idle intervals; never simulate wall-clock time or individual empty ticks.
- Reject signs, suffixes, extra fields, unsafe line lengths, duplicate IDs, invalid IDs, count/range/sum violations, and NUL bytes.

## Concrete hypotheses and experiments

1. **Boundary hypothesis:** `A 0 2`, `B 1 1`, quantum 1 is sufficient to distinguish the exact-boundary rule. The full-output test confirmed B first runs at 1 and completes at 2; A completes at 3.
2. **Stable-order hypothesis:** insertion sort using only `>` for movement retains input order on equal arrivals. `test_input_order_tie_and_output_order` and 80 seeded reference comparisons confirmed that behavior for tested workloads.
3. **Failure-atomicity hypothesis:** keeping parsed tasks temporary and delaying `write_report` makes a bad later line unable to leak an earlier task line. The `2x` test observed nonzero status, a diagnostic, and empty stdout.
4. **Idle-accounting hypothesis:** event jumps can add `next_arrival - clock` without affecting dispatch order. The two-gap case produced elapsed 11, idle 8, and three dispatches.
5. **Resource hypothesis:** one owner in `main`, plus transfer-on-success parsing, makes cleanup paths auditable. Invalid-input cases and all normal cases ran repeatedly; a requested sanitizer build was attempted but unavailable at link time.

## Lessons retained

- Tooling compatibility is part of reproducibility. The initial test harness assumed newer `subprocess` keywords than Python 3.6 provides; portable `PIPE` and `universal_newlines=True` fixed it.
- An expected-output test can be wrong independently of the implementation. Deriving the queue trace explicitly and adding an independent seeded event model made oracles easier to audit.
- Runtime invariant checks are affordable under a 128-task cap and localize state/queue bugs better than relying only on final output.
- A failed tool check is evidence only of a limitation. Missing sanitizer runtime libraries and absent Valgrind/GDB are recorded, not converted into a memory-safety claim.
