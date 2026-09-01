# Independent Rubric: Deterministic Scheduler Kickoff

This file is examiner-only. Evaluate submitted behavior and durable evidence; do not award credit for a learner's unsupported completion claim. Run commands from a clean submission state with bounded execution time. Use fresh evaluator-created inputs in addition to learner tests.

## Decision rule

Score out of 100. Pass the kickoff unit only when all of the following hold:

- total score is at least 75;
- Scheduling Semantics earns at least 24/30;
- Input, Output, and Failure Atomicity earns at least 12/15; and
- no critical failure applies.

A pass means only this manager-authored kickoff unit is complete. It does not establish completion or credit for CS162 or any official assignment.

## Scoring

### Build and reproducibility — 10

- 4: a clean `make` produces `rrsim` non-interactively as C17.
- 2: the required warning flags are present and the submitted code builds without warnings.
- 2: `make test` is unattended, deterministic, and returns a meaningful status.
- 2: `make clean` followed by build and test agrees with recorded evidence; evidence does not substitute for execution.

### Scheduling semantics — 30

- 8: arrivals are ordered by time then input order, and simultaneous initial arrivals are stable.
- 8: round-robin slicing, completion, requeueing, and first-run recording are correct.
- 6: arrivals at a slice-ending boundary precede requeue of the unfinished task.
- 4: idle jumps and idle accumulation are correct.
- 4: turnaround, waiting, elapsed, and dispatch count are correct.

Required-example oracle for quantum 2:

```text
TASK A 0 9 9 4
TASK B 2 8 7 4
TASK C 4 5 3 2
SUMMARY 9 0 6
```

An endpoint-order discriminator is quantum 2 with `A 0 4` and `B 2 1`. Its oracle is:

```text
TASK A 0 5 5 1
TASK B 2 3 1 0
SUMMARY 5 0 3
```

An initial-idle check is quantum 3 with `D 4 2`. Its oracle is:

```text
TASK D 4 6 2 0
SUMMARY 6 4 1
```

### Input, output, and failure atomicity — 15

- 5: all valid lexical forms, comments, blank lines, unsorted records, IDs, and documented bounds are handled.
- 5: empty input, duplicate IDs, signs or suffixes, extra fields, overlong data, range violations, excess counts/service, bad quantum, and file failures return nonzero without crashing.
- 3: failed runs leave standard output empty and give a useful standard-error diagnostic.
- 2: successful formatting, input-order rows, whitespace, and final newline match the contract exactly.

Test lexical edge cases independently; `strtol`/related calls without complete end-pointer, range, and conversion checks do not earn full credit.

### C design and resource safety — 15

- 4: parsing, queue/scheduler behavior, and reporting have coherent interfaces rather than one monolithic routine.
- 4: ownership and cleanup are clear on successful and failed paths; evaluator memory checks reveal no invalid access, use-after-free, or leak attributable to the program.
- 3: arithmetic and conversions are safe for all public limits.
- 2: the ready queue and task state cannot silently duplicate or lose a task.
- 2: diagnostics and return paths are consistent and maintainable.

### Test quality — 15

- 6: black-box assertions check complete output for normal, tie, boundary-arrival, and idle cases.
- 4: negative tests check status, empty standard output, and relevant standard error across distinct parser failures.
- 3: at least one test would fail for each of these plausible mutations: unstable same-time order, requeue-before-endpoint-arrival, and incorrect idle accounting.
- 2: tests avoid wall-clock timing, network access, and order-dependent residue.

### Documentation — 5

- 3: `DESIGN.md` accurately documents modules, transitions, at least three useful invariants, ownership, integers, and a reasoned rejected design within the word limit.
- 1: `TESTS.md` connects cases to observable oracles.
- 1: `EVIDENCE.txt` is fresh, reproducible, and honest about unavailable tools.

### Comprehension — 10

Award roughly equal credit across the eight prompts, then round to a whole number. Strong responses are consistent with the implementation and:

- distinguish state membership, remaining-service bounds, conservation of service, and stable queue order as invariants;
- reproduce the required-example oracle and dispatch sequence;
- use an endpoint-arrival counterexample equivalent in effect to the oracle above;
- distinguish policy from parsing, queue storage, reporting, and cleanup mechanisms;
- trace a real failure path without partial normal output;
- justify integer ranges and conversion checks quantitatively;
- state costs using task count, dispatch count, and input size; and
- identify a credible seam for adding priority scheduling without pretending it is already implemented.

## Critical failures

Do not pass if any of these applies:

- the submitted implementation cannot build or cannot execute a valid workload;
- normal output is substantially hard-coded to supplied examples;
- invalid input can trigger evaluator-observed memory corruption or uncontrolled execution;
- the implementation depends on network access, unavailable external course content, or real-time sleeps;
- core deliverables or all comprehension responses are missing; or
- the submission claims or embeds restricted/hidden course material as evidence.

Preserve evaluator commands, fresh test inputs, outputs, exit statuses, and the final score breakdown as durable evidence.
