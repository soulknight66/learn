# Kickoff 01 submission

Status: **bounded kickoff attempt prepared; native C++ validation blocked by the local toolchain.** This submission makes no claim of completing CS144 or any broader networking course.

## What is submitted

- `src/byte_stream.hh` and `src/byte_stream.cc`: the required C++17 interface and circular-buffer implementation.
- `tests/byte_stream_test.cc`: deterministic public-interface tests, including focused boundaries and a 12,000-operation fixed-seed reference model.
- `CMakeLists.txt`: library, test executable, CTest registration, warnings, C++17/no-extensions settings, and optional sanitizer flags; it downloads nothing.
- `DESIGN.md`: contract table, invariants, ownership, complexity, and the rejected prefix-erasing representation.
- `TESTING.md`: exact commands, tool identities, observed environment failures, and the validation boundary.
- `COMPREHENSION_ANSWERS.md`: responses to all eight local prompts and the requested trace table.
- `notes.md` and `debugging-log.md`: learning notes and reproducible hypothesis/experiment/failure records.

## Result

The implementation owns a capacity-sized ring, head index, and buffered count. It accepts only the fitting prefix, preserves logical order across physical wrap, advances removals without shifting survivors, and keeps closure and diagnostic error as independent sticky flags. The conservation invariant is `bytes_pushed - bytes_popped == buffered_bytes`.

The test source covers zero capacity and zero lengths, empty access, exact fill and overflow, caller-retained suffixes, interleaving, storage reuse, null bytes, both close states, idempotence, post-close rejection, error independence, and counter accounting. Model failures report the committed seed and operation index.

Native validation did not run: CMake could not locate `CMAKE_ROOT`, and direct GCC compilation could not execute `cc1plus`. An independent 12,000-operation Python state-model experiment passed, including 114 wrap events, but that is not a substitute for compiling and executing the C++ tests. The next required action is the clean workflow in `TESTING.md` on a complete C++17 environment, followed by sanitizer execution if available.
