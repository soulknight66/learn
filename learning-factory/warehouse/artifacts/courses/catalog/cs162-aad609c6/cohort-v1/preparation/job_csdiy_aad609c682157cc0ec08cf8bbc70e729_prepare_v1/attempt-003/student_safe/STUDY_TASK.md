# Study Task: Build `rrsim`

## Objective and timebox

Implement a deterministic round-robin scheduling simulator in portable C17. Spend about 8 hours and stop at 10 hours. If unfinished, submit the best reproducible state and document the remaining gap; do not hide missing behavior.

The simulator models scheduling decisions only. Do not create operating-system threads, sleep, use wall-clock time, or attempt a Pintos/CS162 project.

## Public command contract

The program is invoked as:

```text
./rrsim -q QUANTUM INPUT
```

`QUANTUM` is a base-10 integer from 1 through 1,000,000 inclusive. `INPUT` is a path to a text file. Extra or missing arguments are errors.

Use only the C standard library for the submitted implementation. The program must build as C17 without compiler warnings under:

```text
-std=c17 -Wall -Wextra -Wpedantic
```

### Input format

- A blank line is ignored.
- A line whose first non-whitespace character is `#` is ignored.
- Every other line has exactly three whitespace-separated fields: `ID ARRIVAL SERVICE`.
- `ID` matches `[A-Za-z][A-Za-z0-9_-]{0,15}` and is unique.
- `ARRIVAL` is a base-10 integer from 0 through 1,000,000.
- `SERVICE` is a base-10 integer from 1 through 1,000,000.
- There must be 1 through 128 tasks, and the sum of all service values must not exceed 10,000,000.
- Task lines need not be sorted. “Input order” always means their order among non-comment task lines.
- Signs, numeric suffixes, extra fields, overlong lines that cannot be safely processed, and values outside the ranges above are invalid.

### Scheduling semantics

Time is an integer boundary beginning at `t = 0`. Each task moves through not-arrived, ready, running, and completed states.

1. At a boundary, add every task arriving then to the tail of the ready queue in input order.
2. If the CPU is free and the queue is nonempty, remove its head and dispatch it. Record its first-run time on its first dispatch. Each removal from the ready queue counts as one dispatch.
3. Run the task until it completes or consumes one quantum, whichever comes first. A dispatch has no time cost.
4. Tasks arriving strictly during that interval join the tail at their arrival boundaries, ordered first by arrival and then by input order.
5. At the ending boundary, enqueue tasks arriving exactly then before requeueing an unfinished running task. A completed task is never requeued.
6. If no task is ready, advance directly to the next arrival and add the skipped duration to idle time.

There is no context-switch cost. All timing arithmetic must be represented safely for the stated limits.

For each task:

- `turnaround = completion - arrival`
- `waiting = turnaround - service`

### Successful output

Write no header. Write one task line per task in input order, followed by exactly one summary line:

```text
TASK ID FIRST_RUN COMPLETION TURNAROUND WAITING
SUMMARY ELAPSED IDLE DISPATCHES
```

The words shown in uppercase are literal; the remaining fields are base-10 integers or the original `ID`. Separate fields with one ASCII space. End every line with a newline. `ELAPSED` is the final completion time measured from `t = 0`.

### Failure behavior

On an invalid command or input, return a nonzero status, write a concise diagnostic to standard error, and write nothing to standard output. Do not continue with a partial workload. Release all acquired resources on every exit path.

## Required example

Use this as one test input, but derive the expected result yourself:

```text
# ID arrival service
A 0 5
B 1 3
C 2 1
```

Run it with quantum 2. Your test suite must check the complete output rather than checking only that the program exits successfully.

## Deliverables

Submit:

- C source and headers, organized so parsing, scheduling/queue behavior, and output are not one indivisible routine;
- a `Makefile` where `make` builds `rrsim`, `make test` runs unattended tests, and `make clean` removes generated build products;
- `DESIGN.md` of at most 1,000 words describing modules, state transitions, at least three invariants, ownership/cleanup, integer choices, and one rejected design;
- `TESTS.md` listing each test's purpose and observable oracle, including normal scheduling, an input-order tie, an arrival exactly at a slice boundary, initial idle time, malformed input, duplicate ID, range failure, and empty input;
- `EVIDENCE.txt` containing the commands, exit statuses, and outputs from a clean build and test run, plus a memory-safety or debugger check when the needed tool is available; and
- `RESPONSES.md` answering every prompt in `COMPREHENSION.md`.

Do not submit a generated binary as evidence. Do not claim a tool check that you could not run; record the limitation honestly.

## Suggested work sequence

1. Trace the required example on paper and write down the queue-boundary rules.
2. Define task state and module interfaces before implementing the event loop.
3. Build a vertical slice that parses one valid task and produces output.
4. Add scheduling behavior, then failure-atomic parsing and cleanup.
5. Add deterministic black-box tests, including cases designed to distinguish plausible but wrong boundary rules.
6. Clean the workspace, rebuild, run tests, and capture fresh evidence.

The work is ready for evaluation when all deliverables exist, a clean build and unattended test run are reproducible, invalid input cannot emit partial normal output, and the documentation matches the submitted program.
