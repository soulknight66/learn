# Debugging log

This log records observable hypotheses, commands, outcomes, and lessons for kickoff unit `kickoff_01_bounded_byte_stream`. It does not contain private chain-of-thought.

## Environment discovery

- Experiment: attempted a filename-only listing with `rg --files`.
- Result: failed because `rg` is not installed (`/bin/bash: rg: command not found`).
- Response: used `find` only to list workspace filenames, then opened exactly the three learner-safe files named by the course brief.
- Lesson: reproduction instructions should rely only on tools actually confirmed in the environment.

## Contract hypothesis before implementation

- Hypothesis: because accepted pushes are the only ingress and pop/read are the only egress, `bytes_pushed - bytes_popped` must equal `buffered_bytes` after every operation.
- Planned experiment: assert that conservation law, the capacity equation, and a reference payload after every step of a fixed-seed sequence of at least 10,000 operations.
- High-risk cases: capacity zero, modulo at physical wrap, oversized removal, rejected push after close, and error-state coupling.

## Red-test baseline

- Hypothesis: a compiling stub whose `push` returns zero should fail an exact-fill test expecting three accepted bytes.
- Experiment: created the CMake target, interface, stub, and one exact-fill test, then ran `cmake -S . -B build`.
- Failure: configuration stopped before compiling the project because CMake 3.26.5 could not find `CMAKE_ROOT`; therefore the expected behavioral failure was not observable.
- Follow-up experiment: invoked GCC directly with `c++ -std=c++17 -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Isrc src/byte_stream.cc tests/byte_stream_test.cc -o build/byte_stream_test`.
- Failure: the GCC 8.5.0 driver could not execute `cc1plus`. `g++ -print-prog-name=cc1plus` returned only the unresolved program name, and no `clang++` was available on `PATH`.
- Lesson: an authored failing test is not red-test evidence unless it executes. The environment failure must be reported separately from product behavior.

## Implementation experiment

- Hypothesis: head plus live size uniquely represents empty and full ring states, and each push/peek needs no more than two contiguous copies.
- Change: implemented fixed storage, split copies, O(1) head advancement, counters, and independent sticky flags. Added focused black-box tests plus a 12,000-operation fixed-seed deque model.
- Static review checks: every modulo operation is unreachable at capacity zero; `string_view` data is copied rather than retained; zero-byte operations leave counters unchanged; resetting head on empty is internal only.
- Native outcome: not executed because both available build paths fail before source compilation. No pass claim is based on inspection.

## Independent state-model experiment

- Experiment: ran an equivalent ring-state prototype against a bytearray reference using seed `7739826747694540337` for 12,000 mixed operations. It checked payload equality, capacity equations, counters, closed/error observations, zero-length behavior, and wraparound after every operation.
- Result: passed with 114 physical wrap events, 32,745 accepted bytes, 32,745 removed bytes, and an empty closed/error final state.
- Lesson: the experiment increases confidence in the representation and generator logic, but it cannot reveal C++ compilation, lifetime, iterator, or undefined-behavior defects. It is supporting evidence only.

## Remaining blocker

A machine with complete CMake modules and a C++17 compiler backend must run configure, build, CTest, and preferably AddressSanitizer/UndefinedBehaviorSanitizer. Until then, the kickoff implementation is prepared but not validated.
