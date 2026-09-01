# Revision Debugging Log

Course unit: `kickoff_slp_interpreter_v1`  
Learner validation label: `LEARNER_REVISED_SELF_CHECKED_UNVALIDATED`

This records commands, controlled experiments, and observable results. It does
not record private chain-of-thought.

## 2026-08-31 — Initial revision inventory

Command:

```bash
find . -path './.git' -prune -o -type f -print | sort
```

Observation before implementation: the writable root contained the supplied
learner material, prior-attempt records, examiner feedback, and factory marker,
but no CMake project, headers, sources, tests, README, design file, or
comprehension responses. This reproduced the packaging gap named by the
examiner. I did not modify the three read-only input directories.

## 2026-08-31 — Configure and warning-enabled build

Commands:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel 2
```

Observed results: both exited 0. CMake selected GNU C++ 8.5.0, generated the
isolated `build/` tree, compiled all three library sources with
`-Wall -Wextra -Wpedantic`, and linked `slp_demo` and `slp_tests`. No compiler
warning or source build failure appeared. The shell printed UID/GID
name-resolution diagnostics before commands; these environmental messages did
not change their exit status.

## 2026-08-31 — Registered test run

Command:

```bash
ctest --test-dir build --output-on-failure
```

Observed result: exit 0; CTest discovered `slp_behavior`, reported 1/1 passed,
0 failed, and completed in 0.01 seconds.

## 2026-08-31 — Direct behavioral observations

Commands:

```bash
./build/slp_tests
./build/slp_demo
```

Both exited 0. The test runner printed `PASS` for all 17 named cases and ended
with `17 test(s) passed`. The demo emitted `4 14 7` followed by one newline.

The controlled failure cases returned their asserted categories instead of
terminating: `InvalidAst`, `UnboundName`, `AdditionOverflow`,
`SubtractionOverflow`, `MultiplicationOverflow`, `DivisionByZero`,
`DivisionOverflow`, and `OutputFailure`. In the failing outer-print case, exact
retained bytes were `9\n`, `x` remained 2, and the later expression assigning
99 was not visited. In the failed-assignment case, `x` remained 5, the earlier
side binding remained 7, and the later `tail` statement was not visited.

## 2026-08-31 — Explicit staged-copy rehearsal

I created a new `stage-check-*` scratch directory and copied an explicit
artifact list: `.gitignore`, the root CMake file, all three public headers, all
three implementation sources, the demo, test source, README, design record,
comprehension responses, and the three fresh learner records. I excluded the
read-only input directories and existing generated build tree.

Checks and commands:

```bash
cmp <each-original> <each-staged-copy>
cmake -S ./stage-check-* -B ./stage-check-*/build -DCMAKE_BUILD_TYPE=Debug
cmake --build ./stage-check-*/build --parallel 2
ctest --test-dir ./stage-check-*/build --output-on-failure
```

Observed result: every byte comparison exited 0. Configure and build exited 0,
and the CTest run in the newly copied project exited 0 with 1/1 tests passed
and 0 failed. This is a reproducible local staging experiment, not evidence
that an external transfer or independent validation has occurred.

## Current watch items

- Recursive interpreter and analysis calls are susceptible to stack exhaustion
  on a sufficiently skewed tree.
- Language-level print buffering prevents partial lines on expression failure;
  it cannot make an arbitrary external stream transactionally atomic.
- All results above are learner self-check evidence. Independent harness
  validation has not been claimed.

## Provenance

Only the supplied kickoff specification and read-only revision context were
used. No external resource, framework, sealed material, rubric, or other
learner submission was consulted.
