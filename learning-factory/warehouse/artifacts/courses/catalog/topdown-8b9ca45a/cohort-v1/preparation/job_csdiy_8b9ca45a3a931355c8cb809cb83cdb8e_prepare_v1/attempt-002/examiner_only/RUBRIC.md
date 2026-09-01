# Independent examiner rubric — HTTP exchange kickoff

This rubric assesses only `kickoff_application_layer_http_v1`. It must not be used to infer completion of the full course. Evaluate the learner's actual repository in a clean process; prose claims and screenshots alone are not evidence. External course links, the textbook, Wireshark, and internet access are not assessment prerequisites.

## Examination procedure

1. Record the submitted commit or artifact hash and the documented runtime/tool versions.
2. Follow only the submitted build and test commands in an environment with public-network access disabled.
3. Inspect the source to confirm that the fixture binds to loopback on an ephemeral port and that the client does not shell out.
4. Run the learner's tests, then run examiner-controlled cases using an independent scripted loopback server. Vary fragment boundaries, delays, malformed bytes, and response sizes rather than trusting fixture claims.
5. Compare the saved evidence with a fresh successful run. Redact and stop if any secret or unrelated captured traffic appears.
6. Score comprehension responses for reasoning tied to implementation evidence; do not award credit for terminology alone.

## Scoring (100 points)

### Protocol contract and byte fidelity — 18 points

- 6: Emits a syntactically valid HTTP/1.1 `GET` request containing a correct `Host` field and connection-close request, with a loop that handles partial writes.
- 5: Validates the status line and header syntax; treats field names case-insensitively without corrupting body bytes.
- 4: Correctly retains bytes following the first complete end-of-head delimiter, including non-text body data.
- 3: Detects unsupported transfer coding explicitly rather than claiming to decode it.

### Streaming state and fragmentation — 20 points

- 8: Finds a delimiter split at every examiner-selected boundary, including one-byte delivery, without assuming read/message alignment.
- 5: Maintains a coherent state or invariant across reads and handles bytes already received beyond the delimiter.
- 4: Generated fragmentation tests reuse a canonical expected response and are deterministic on failure.
- 3: I/O and parse logic are separated enough to exercise boundary behavior directly.

### Failure handling and resource bounds — 20 points

- 4 each: examiner-observable, distinct handling for timeout; EOF before a complete head; malformed status/header syntax; connection failure; and head or total size-limit breach.
- Full credit requires a per-operation timeout, head limit at most 64 KiB, total limit at most 1 MiB, and deterministic nonzero failure results. Merely documenting a limit earns no credit if the executable does not enforce it.

### Test quality and reproducibility — 20 points

- 8: Automated tests cover all cases listed in `STUDY_TASK.md` and make no public-network request.
- 5: The fixture is isolated, uses an ephemeral loopback port, cleans up processes/sockets, and avoids timing races where practical.
- 4: A clean checkout/process can run the documented commands without undocumented manual setup.
- 3: Failures identify the case, fragmentation, and observed result sufficiently to reproduce them.

### Engineering explanation and evidence — 12 points

- 4: Design note accurately states parser states and an invariant consistent with the code.
- 3: README gives exact commands, versions, assumptions, and bounded non-goals.
- 3: Sanitized evidence unambiguously records request bytes, fixture delivery chunks, parsed metadata, body count, and exit result and agrees with a fresh run.
- 2: Tradeoffs connect observed risks to specific design decisions; no completion claim substitutes for evidence.

### Comprehension — 10 points

Award one point for each prompt when the response is accurate, specific, and supported by the learner's implementation or tests. Expected indicators are:

1. Separates TCP connection/stream semantics, receive-call boundaries, HTTP head framing, and possibly body framing.
2. Tracks accumulated suffix or equivalent state across all fragments and does not consume body bytes as headers.
3. Identifies cross-fragment delimiter loss; describes bounded carry-over or bounded accumulation without repeated unbounded copying.
4. Identifies case-insensitive field names while preserving semantically relevant values and arbitrary body bytes, backed by mixed-case and binary tests.
5. Distinguishes peer termination, elapsed waiting, and local policy enforcement as different diagnoses and retry/security signals.
6. Describes deterministic partition generation and recognizes that finite partitions do not cover all timing, concurrency, or protocol cases.
7. Gives complexity consistent with the implementation and notices risks such as repeated concatenation or rescanning from the beginning.
8. Limits application traces to bytes exposed at the socket API; packet captures add segmentation/timing/flags but neither alone proves general correctness or remote intent.
9. Identifies chunk-size parsing, extensions/terminators/trailers, overflow and cumulative bounds, fragmentation, and malformed or truncated cases.
10. Names a genuine production gap and proposes executable, reviewable evidence rather than confidence alone.

## Decision rules

- Pass this unit at 80 or more points only if all critical gates below pass.
- Critical gates: runnable automated tests; no public-network dependency; partial-write handling; cross-read delimiter handling; enforced timeout and both size limits; deterministic rejection of incomplete/malformed heads; and no secrets or unrelated traffic in evidence.
- A critical-gate failure caps the result at 69. Missing runnable implementation or fabricated evidence caps it at 39.
- Examiner infrastructure failure is `NOT_EVALUATED`, not learner failure. Preserve logs and rerun deterministically after repair.
- A passing rubric result is evidence for this kickoff unit only. Only the worker-harness-controlled validator may promote unit state, and it must leave whole-course completion unestablished.
