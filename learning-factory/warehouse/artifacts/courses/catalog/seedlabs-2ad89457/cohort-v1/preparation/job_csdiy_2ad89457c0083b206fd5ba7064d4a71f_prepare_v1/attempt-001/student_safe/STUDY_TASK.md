# Study Task: Boundary-Safe Binary Frame Encoder

Artifact classification: manager-authored learner assignment  
Validation label: PREPARED_UNVALIDATED  
Timebox: 4–6 hours

## Assignment

Build a small C11 library function that encodes a byte sequence as a two-byte, unsigned big-endian payload length followed by the payload. The assignment is intentionally narrow: the engineering quality of the contract, failure behavior, tests, build, and evidence matters as much as the happy-path output.

Use this public interface (you may add documentation, include guards, and internal helpers, but do not change the observable contract):

```c
#include <stddef.h>
#include <stdint.h>

typedef enum {
    FRAME_OK = 0,
    FRAME_INVALID_ARGUMENT,
    FRAME_TOO_LARGE,
    FRAME_NO_SPACE
} frame_status;

frame_status frame_pack(const uint8_t *src,
                        size_t src_len,
                        uint8_t *dst,
                        size_t dst_cap,
                        size_t *written);
```

## Required contract

- A successful frame contains exactly two length bytes followed by exactly `src_len` payload bytes. The length bytes represent `src_len` in unsigned big-endian order.
- Payloads larger than 65,535 bytes return `FRAME_TOO_LARGE`.
- `written` must be non-null. When it is valid, set it to zero before any other validation; on success, set it to the complete frame length.
- `dst` must be non-null because even an empty payload produces a two-byte frame. `src` may be null only when `src_len` is zero. Contract violations return `FRAME_INVALID_ARGUMENT`.
- If the destination cannot hold the complete frame, return `FRAME_NO_SPACE`.
- Every failure leaves all bytes in a non-null destination unchanged. The function performs no allocation, I/O, logging, or mutation of global state.
- Source, destination, and `written` storage do not overlap. Overlap is outside this unit's contract; document that precondition rather than expanding the assignment.
- Validation precedence is: invalid arguments, oversized payload, insufficient destination. This makes mixed-error cases deterministic.

## Work products

Create a small repository-shaped submission containing:

- `include/frame.h` — the public interface and caller-visible contract;
- `src/frame.c` — the implementation;
- `tests/test_frame.c` — a deterministic, self-checking test executable;
- `Makefile` — at least `all`, `test`, `sanitize`, and `clean` targets;
- `DESIGN.md` — assumptions, preconditions, invariants, error precedence, and a short argument connecting checks to writes;
- `TEST_EVIDENCE.txt` — exact commands run, compiler version, exit status, and captured summary for normal and sanitizer builds; and
- `COMPREHENSION_RESPONSES.md` — your numbered responses to `COMPREHENSION.md`.

Do not include generated binaries, downloaded course material, credentials, or machine-specific absolute paths.

## Engineering constraints

- Compile as C11 with warnings enabled (`-Wall -Wextra -Wpedantic` or documented equivalents); treat project warnings as errors.
- Use no unbounded string-copy or formatting functions. Remember that the payload is binary and may contain zero bytes.
- Keep the build offline and deterministic. Tests must need no network, clock, randomness, locale, elevated privilege, or external service.
- The normal test target must work without sanitizers. The sanitizer target should use AddressSanitizer and UndefinedBehaviorSanitizer when the local compiler supports them.
- A missing sanitizer is an honestly recorded environment limitation, not permission to claim a sanitizer pass.

## Required test coverage

Your test suite must make failures visible through a nonzero process exit and cover at least:

- empty and one-byte payloads;
- binary data containing embedded zero bytes;
- lengths that exercise both length-prefix bytes, including the 255/256 transition;
- exact destination capacity and one byte too little;
- null-pointer cases defined by the contract;
- the maximum encodable length and a value just above it;
- a representatively huge `size_t` length that must be rejected before reading the source;
- destination sentinel bytes proving every reachable failure path is non-mutating; and
- a deterministic loop over a useful range of valid payload lengths, checking both encoded length and byte preservation.

Tests should report which case failed without depending on test execution order. Do not weaken or skip an assertion merely to obtain a green run.

## Suggested sequence

1. Write the contract table and invariants in `DESIGN.md`.
2. Derive a boundary-focused test table before implementing.
3. Implement the smallest code that satisfies the contract.
4. Run the normal build and test target from a clean tree.
5. Run the sanitizer target if supported, then record exact evidence.
6. Review the diff as if it came from a teammate and answer the comprehension prompts.

At six hours, stop expanding scope. Submit working evidence plus an explicit blocker note for anything unfinished. Do not turn this kickoff into an exploit exercise or an attempt to complete the broader course.

Provenance: newly authored kickoff seeded only by the catalog's mention of C and a buffer-overflow lab example; no linked lab, video, textbook, or environment content was retrieved.
