# Examiner Rubric: Epoch-Fenced ParcelQ

## Handling and authority

This file is examiner-only. Do not copy its scoring rules, thresholds, expected results, or novel checks into `student_safe/` or a learner submission.

Evaluate only the preserved learner artifacts `lease_queue.py`, `test_lease_queue.py`, `DESIGN.md`, and `INCIDENT.md`, plus results you reproduce under a bounded local harness. The prepared packet and learner prose are not proof of behavior. A rubric result is bounded to this locally authored exercise; it gives no official assignment credit and must leave course completion `NOT_CLAIMED`. Only the worker-harness-controlled validation path may promote an independently examined attempt.

## Examination protocol

1. Record the submitted file list and immutable digests before execution.
2. Read the declared run command and inspect for network, wall-clock, sleep, randomness, thread, subprocess, or out-of-submission dependencies.
3. Run the learner tests from a clean copy with network unavailable and a 30-second process timeout. Capture stdout, stderr, exit status, and duration.
4. Run `NOVEL_CHECK.md` cases independently. A thin adapter for harmless naming differences is allowed and must be preserved; do not repair learner semantics.
5. Compare response values, full state, request history, installed fence, and ordered log landmarks. A final-state-only match is insufficient.
6. Record each awarded item with a file/line reference or reproduced command and observation. Unsupported prose claims receive no credit.

## Scoring (100 points)

### A. Scope and model contract — 10 points

- **4 points:** `DESIGN.md` accurately distinguishes the locally authored exercise from the linked normalized catalog record and makes no official-unit, course-completion, or production-correctness claim.
- **3 points:** The state, half-open lease interval, logical request payload, authoritative time source, and trust boundary are explicit and consistent with code.
- **3 points:** Non-goals include real clocks/skew, coordinator failover, multi-process races, storage failures, and Byzantine or cryptographic enforcement; the exact required closing scope statement is present.

### B. Lease, fence, and request correctness — 35 points

- **8 points:** Grants obey the expiry boundary, positive TTL, monotonic no-gap epochs, and denial-without-side-effects rule. Fence installation and publication of a grant are atomic, including the failure path.
- **10 points:** The queue validates exact owner, epoch, interval, and logical-time validity against the installed lease. Stale, forged-future, altered, premature, and expired tokens cannot mutate state or history.
- **9 points:** History lookup precedes authority checks for an existing ID; exact-payload replay returns the exact historical response, payload mismatch is `ID_CONFLICT`, and neither path mutates state. A first fenced attempt is not recorded.
- **8 points:** `CLAIM`, `COMPLETE`, missing-job, invalid-action, wrong-worker, repeated-business-operation, and completed-job behavior is deterministic. Every fence-authorized state-machine result is recorded once, including nonmutating business results.

### C. Determinism and public evidence — 20 points

- **8 points:** All six required public traces assert response, job state, history, fence, and log landmarks rather than only checking for an exception or final value.
- **5 points:** Events are ordered by `(tick, insertion_index)` with a monotonic tie-breaker; repeated fresh runs are byte-for-byte or structurally identical.
- **5 points:** Structured records are ordered and expose the requested fields, including presented versus active authority and before/after state. Logging is observational rather than behavior-changing.
- **2 points:** Tests are isolated, have no order dependence, and run with the documented standard-library command from a clean submission.

### D. Debugging evidence — 15 points

- **6 points:** `INCIDENT.md` preserves at least three genuinely distinct hypothesis → experiment → observation → revision cycles tied to defects in the unsafe excerpt.
- **4 points:** Each experiment has a minimal reproducible event trace, exact run command, assertions, and relevant structured-log evidence.
- **3 points:** At least one initial hypothesis is refined or rejected in response to observed evidence rather than narrated as hindsight.
- **2 points:** Failed experiments and unresolved questions remain visible and are not recast as successful results.

### E. Production reasoning and maintainability — 10 points

- **4 points:** The design explains why node-local expiry checks alone cannot enforce safety and identifies the modeled atomic control-plane boundary.
- **3 points:** The production-gap discussion proposes concrete mechanisms or experiments for real clocks, durable transactions, coordinator replication, authentication, process concurrency, and operational recovery without claiming they were implemented.
- **3 points:** State transitions, authority validation, history behavior, and event scheduling are separated enough to inspect and change without hidden coupling.

### F. Novel transfer checks — 10 points

- **10 points:** Award two points for each of Novel Checks N1–N5 only when the reproduced observations match. N6–N8 are diagnostic cross-checks used to confirm the applicable categories above.

## Decision rule

A candidate unit pass requires at least 80/100, all four learner artifacts, a clean learner-test exit, and successful Novel Checks N1, N2, N4, and N5. It also requires none of the critical failures below. Report the numeric score and evidence, but do not report course completion.

### Critical failures

- An unseen stale, expired, wrong-owner, altered, or uninstalled-future token changes job state or request history.
- A duplicate accepted request produces a second state transition, or an ID conflict overwrites history.
- A failed or denied grant leaves a visible partial fence/current-lease update or consumes an epoch.
- Correctness depends on wall-clock time, sleep, randomness, event-container accident, network access, or files outside the preserved submission.
- The learner tests do not run from a clean copy, or claimed evidence cannot be reproduced.
- The submission claims official assignment credit, production correctness, transfer, or course completion, or omits the required scope statement.

If execution is unsafe or impossible, preserve the reason and mark the result `INCONCLUSIVE` or `FAIL` according to the harness protocol; never infer success from prose.
