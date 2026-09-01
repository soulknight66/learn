# Kickoff 01 study notes

Scope: the manager-authored bounded byte-stream kickoff only. These notes do not represent completion of CS144 or of a networking curriculum.

## Contract extraction

- Capacity is fixed, including the valid zero-capacity case.
- The producer transfers ownership only of the accepted prefix; `push` must return its exact length.
- Closure stops ingress but does not flush accepted bytes. Finished means the conjunction of closed and empty.
- The error bit is orthogonal diagnostic state. It must not be used as an implicit close or reset.
- Counters measure actual transfers, not requests: accepted bytes in and removed bytes out.
- Arbitrary bytes make explicit lengths essential; C-string operations would mishandle embedded nulls.

Useful conservation law: `bytes_pushed - bytes_popped == buffered_bytes`. Together with `remaining_capacity + buffered_bytes == capacity`, this gives a compact post-operation check for both implementation and model tests.

## Initial engineering hypothesis

A ring buffer should meet the repeated-small-removal requirement without exposing its representation. The minimum state is fixed storage, a logical head, a live-byte count, two cumulative counters, and closed/error flags. A separate live-byte count disambiguates empty from full when head and tail indices coincide.

The main risk areas to probe are zero capacity (no modulo), split copies at wraparound, counter changes on oversized/rejected operations, and the lifecycle state closed-but-not-finished.

## Worked contract trace

For capacity five, `push("abc")` accepts three. `peek(2)` returns `ab` without changing state. `push("WXYZ")` accepts only `WX`, filling the buffer with `abcWX`; `YZ` remains the caller's responsibility. `pop(4)` leaves `X`. Closing now makes the stream closed but not finished. A later `push("!")` returns zero. `read(10)` returns `X`, after which the stream is both closed and empty, hence finished. Final counters are five pushed and five popped.

This trace exposed a useful distinction: physical room after the pop does not permit a push after close. Capacity and lifecycle are separate acceptance conditions.

## Test strategy notes

Focused examples should name one boundary or transition at a time. I used cases for zero-length and zero-capacity operations, empty access, overflow and caller-owned suffixes, wraparound reuse, embedded nulls, close states, diagnostic error independence, and exact accounting. These tests should make a future regression small enough to understand.

The larger test uses a reference deque and fixed xorshift seed `0x6b69636b6f666631` for 12,000 operations. After each operation it compares the complete visible payload and every query, including the conservation law. Seed and operation index are part of failure reports. The model test broadens interaction coverage; it does not replace the focused cases.

## Systems and production-engineering lessons

- Partial acceptance is backpressure, not a lossy convenience. A correct caller retains and retries the suffix in order.
- API lifecycle words need exact predicates. “Closed” describes producer permission; “finished” also includes consumer progress.
- A representation choice is part of externally observable performance even when private. Prefix erasure would pass small functional examples but fail the repeated-removal target.
- Ownership belongs in the design record: copy from the transient `string_view`, and return owning strings.
- Test source, a passing model analogy, and an executed native test suite are different grades of evidence. Here the installed CMake and compiler driver were incomplete, so the C++ artifact remains unvalidated.

## Boundary of this attempt

I prepared the kickoff component, its tests, design, testing record, and comprehension response. I did not study packet formats, layering, routing, transport, congestion control, official lab material, or any other course unit. A complete C++17 toolchain must still run the recorded commands before this kickoff can be treated as validated.
