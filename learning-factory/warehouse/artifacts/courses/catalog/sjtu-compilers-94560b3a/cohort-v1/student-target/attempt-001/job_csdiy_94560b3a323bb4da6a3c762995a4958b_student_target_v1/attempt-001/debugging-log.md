# Debugging Log

Course unit: `kickoff_slp_interpreter_v1`  
Learner validation label: `LEARNER_SELF_CHECKED_UNVALIDATED`

This log records reproducible observations and controlled failure cases, not
private reasoning.

## 2026-08-31 — Initial configure

Command:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Debug
```

Hypothesis: the public construction-key pattern and C++17 variant visitors are
accepted by the available toolchain. Result: exit 0 with GNU C++ 8.5.0; CMake
configured and generated the isolated `build/` directory. The shell emitted
environmental UID/GID name-resolution diagnostics before CMake, but they did
not affect configuration.

## 2026-08-31 — Initial warning-enabled build

Command:

```bash
cmake --build build --parallel 2
```

Result: exit 0. The library, demonstration, and test executable linked. No
compiler warnings or implementation build failures were observed on this first
build; no failure was invented for this log.

## 2026-08-31 — Initial deterministic test run

Command:

```bash
ctest --test-dir build --output-on-failure
```

Result: exit 0; CTest reported 1/1 suite passed and 0 failed. The suite contains
14 named cases. Important deliberately triggered failures all produced the
expected structured result rather than aborting:

- missing name -> `UnboundName`;
- zero divisor -> `DivisionByZero`;
- addition, subtraction, multiplication, and special division overflow ->
  their distinct overflow categories;
- null root -> `InvalidAst`;
- rejecting output stream -> `OutputFailure`.

The failing-print experiment retained exact output `"9\n"`, suppressed the
outer line, and retained `x = 2`. The failed-assignment experiment retained the
old target `x = 5` and the already-completed side binding `side = 7`.

## 2026-08-31 — Direct fixture checks

Commands:

```bash
./build/slp_demo
./build/slp_tests
```

Both exited 0. The demonstration emitted exactly `"4 14 7\n"`. The direct
test runner listed all 14 named cases as `PASS` and ended with
`14 test(s) passed`. A documentation-only patch initially missed its expected
text context and was reapplied with the correct context; it did not change or
exercise source behavior.

## Current limitations to watch

- Recursive traversal can exhaust the process stack on an extremely deep AST.
- `std::map` makes binding access logarithmic and identifier comparison has a
  string-length cost.
- Logical print buffering protects against expression failure; a physical
  device error can still occur after a stream accepts a byte prefix.
- These are learner self-check observations. An independent harness has not yet
  validated this attempt.

## Provenance

The experiments implement only the supplied kickoff specification in
`COURSE_BRIEF.md`, `STUDY_TASK.md`, and `COMPREHENSION.md`.
