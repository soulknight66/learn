# Independent Examiner Rubric

This rubric evaluates only `kickoff_01_http_over_tcp`. It cannot establish completion of the full catalog course. Examine the submitted artifacts and run tests in a controlled environment with public-network access disabled. Do not accept an agent or learner's prose claim as execution evidence.

## Critical gates

All gates must pass before assigning a passing result:

1. The submission includes inspectable source, automated tests, README, report, and comprehension responses.
2. The documented clean build/test command completes under the harness and produces captured exit status and logs.
3. Core parsing does not delegate to a high-level HTTP client/parser, and tests do not contact a public host.
4. Head and body reads are bounded; timeout behavior exists; non-loopback command-line targets are rejected before connection.
5. The examiner can demonstrate correct behavior under fragmented delivery and at least one malformed/unsupported response.
6. The README identifies the implementation as a bounded teaching client, not production-ready.

If a gate fails, record the specific evidence and cap the result below passing even if the numerical subtotal is higher.

## Scored criteria (100 points)

### A. Contract and protocol reasoning — 15 points

- 13–15: Supported and unsupported behavior is precise and consistent across README, code, and tests. Stream framing is delimiter/length driven; ambiguous cases have explicit policy.
- 9–12: The core subset is clear, with minor omissions or inconsistencies that do not make behavior ambiguous.
- 4–8: Several behaviors are implicit, or parsing relies partly on typical packetization.
- 0–3: No coherent contract or a message-per-receive model.

### B. Design and implementation — 20 points

- 17–20: Transport, framing, parsing, policy, and presentation have effective test seams; byte handling is correct; resources close on all paths; public results/errors are stable and useful.
- 12–16: Generally sound separation and implementation with localized coupling or edge defects.
- 6–11: Happy path works but responsibilities are tangled or important state transitions are unreliable.
- 0–5: Core implementation is missing, delegated, or fundamentally incorrect.

### C. Deterministic verification — 25 points

- 22–25: Reproducibly tests all required success, fragmentation, malformed, EOF, limit, timeout, and target-policy classes; assertions address public behavior and tests avoid sleeps/fixed ports.
- 16–21: Strong suite with a few meaningful boundary cases missing or one source of mild nondeterminism.
- 8–15: Mostly happy-path tests, shallow assertions, or substantial missing failure coverage.
- 0–7: Tests are absent, externally dependent, non-executable, or fail to challenge stream boundaries.

Examiner mutation check: change the scripted source so the head delimiter is split byte-by-byte and so body bytes share the delimiter's final fragment. At least one existing test should already cover each behavior, and the implementation should still pass.

### D. Failure containment and observability — 15 points

- 13–15: Enforces documented head/body caps and timeouts at exact boundaries; distinguishes error categories; closes resources; emits useful stable events without body/sensitive-data leakage.
- 9–12: Controls are present but one boundary, cleanup path, or diagnostic distinction is weak.
- 4–8: Partial controls with unbounded or poorly classified paths.
- 0–3: Hangs, grows without bound, leaks resources, or logs unsafe payload data.

### E. Reproducibility and engineering communication — 10 points

- 9–10: Clean commands are exact and work; layout is maintainable; report provides captured, credible evidence and candid limitations; no generated clutter.
- 6–8: Reproducible with minor documentation or organization problems.
- 3–5: Examiner must infer commands/assumptions or report evidence is weak.
- 0–2: Submission cannot be reproduced or materially misrepresents results.

### F. Comprehension — 15 points

Award approximately equal credit across the eight prompts, using holistic rounding.

Strong responses should establish these examiner-only indicators:

- TCP preserves byte order but not application write/read boundaries; framing follows the first complete head delimiter and then the validated length.
- The supplied trace does not complete the head until the third fragment; the declared five-byte binary body completes only after the fourth. Status/headers become usable only after successful complete-head validation, and the full response only after all five body bytes.
- Missing, duplicate-equal, and duplicate-conflicting framing are all rejected under this assignment's "exactly one" contract; the risk is that inconsistent interpretations create ambiguity and can enable message-boundary or intermediary disagreements.
- Parse, EOF, timeout/transport, and policy-limit errors originate in distinct layers and expose stable categories without leaking payloads or unstable internal exception text.
- A deliberate cross-fragment delimiter test detects packet-boundary coupling; a normal local exchange can be coalesced or split differently across runs and proves little about all fragmentations.
- Timing/byte events can localize phase or progress but cannot prove correctness or identify network cause by themselves; bodies, credentials, and other sensitive values should not be logged.
- Production gaps plausibly include TLS verification, DNS, redirects, proxy behavior, multiple framing modes, interim/no-body statuses, chunked coding, compression, connection reuse, authentication, cancellation, concurrency, privacy, and richer resource/operability controls.
- For total input bytes `n`, a well-designed reader is linear time. Auxiliary space is bounded by configured head plus body caps; repeated immutable concatenation that causes quadratic copying should be identified or avoided.

### Score interpretation

- 85–100: Strong kickoff completion
- 75–84: Kickoff completion
- 60–74: Revision required
- 0–59: Substantial revision required

Passing requires at least 75 points **and** every critical gate. Record the validator command, exit status, relevant log locations, score by section, gate results, and concise defect notes. Promotion authority remains with the worker harness; this document alone does not change job state.

---

Provenance: independently authored examiner criteria for the manager-authored kickoff, based only on the supplied CSDIY catalog snapshot.  
Validation label: `EXAMINER_SPECIFICATION_AWAITING_HARNESS_EXECUTION`.
