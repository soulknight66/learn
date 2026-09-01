# Learner Submission

Course: `course_94560b3a323bb4da6a3c762995a4958b`  
Unit: `kickoff_slp_interpreter_v1`  
Validation label: `LEARNER_SELF_CHECKED_UNVALIDATED`

## Submitted artifacts

- Public C++17 AST factories with immutable shared ownership and construction
  invariant errors
- Interpreter with a fresh environment, injected output, left-to-right effects,
  per-print buffering, and structured errors
- Portable prechecks for signed 64-bit arithmetic
- Pure `max_print_arity` traversal, including prints nested in expressions
- CMake library, demonstration executable, and CTest-registered automated suite
- Build/use documentation, design record, and eight comprehension responses
- Learner notes and a reproducible debugging log

## Learner self-check evidence

On 2026-08-31 in the provided workspace:

```text
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug    exit 0
cmake --build build --parallel 2                exit 0
ctest --test-dir build --output-on-failure      exit 0; 1/1 suite passed
./build/slp_demo                                exit 0; "4 14 7\n"
./build/slp_tests                               exit 0; 14 cases passed
```

The suite contains 14 named behavior cases covering every syntax form,
evaluation order, nested effects, exact whitespace, all requested arithmetic
errors, print suppression, construction invariants, analysis purity, and output
failure. Detailed observations are in `debugging-log.md`.

## Status and boundary

This is a learner attempt at the bounded kickoff unit only. The successful local
commands are self-check evidence, not a claim of worker-harness acceptance. No
lexer, parser, later compiler phase, external framework, or whole-course
completion is claimed.

## Provenance

The implementation and learner artifacts derive only from the supplied
learner-safe `COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`. No
external resource or course framework was used.
