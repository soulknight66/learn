# Examiner-Only Novel Checks

## Purpose and setup

Keep this file and all derived fixtures out of `student_safe/`. These cases probe combinations not enumerated as public traces. Run them against an unmodified clean submission. A small preserved adapter may translate class or field names, but it may not add validation, reorder operations, synthesize history, or repair atomicity.

For each case, capture the exact command, exit status, response objects or values, job snapshots, request-history snapshots, active lease, and relevant ordered log records. Use fresh objects unless the case explicitly continues a prior step.

The expected outcomes below are examiner evidence, not learner hints.

## N1 — Rejected stale first attempt, valid retry, then stale replay

1. Create job `j` as `READY`.
2. Grant owner `A` at tick 0 with TTL 5; expect epoch 1 and interval `[0,5)`.
3. Attempt to grant owner `B` at tick 4; expect denial, active owner `A`, and no consumed epoch.
4. Grant `B` at tick 5 with TTL 4; expect epoch 2 and active interval `[5,9)`.
5. At tick 5, deliver through A the unseen request `q1 = (CLAIM, j, w)`. Expect `FENCED`, `j` still `READY`, and no `q1` history entry.
6. At tick 5, deliver the same logical `q1` through B. Expect `OK_CLAIMED`, `j = CLAIMED(w)`, and one `q1` history entry.
7. At tick 6, deliver exact `q1` through stale A. Expect the exact stored `OK_CLAIMED` response, no mutation, and one history entry.

This passes only if the last step is classified as a history replay while the first A attempt is classified as a fence rejection.

## N2 — Installed-token equality, not “largest epoch wins”

With a valid installed lease for B and fresh jobs, construct each presented token without installing it:

- owner B and the installed epoch, but an altered expiry;
- owner Z and the installed epoch with the otherwise exact interval;
- owner B and epoch 999 with a plausible interval.

Submit a distinct unseen `CLAIM` for each. Every attempt must return `FENCED`, with no state or history mutation. Retry each same logical request through the truly installed B lease while it is valid; each may then reach the business state machine. Accepting epoch 999, comparing only `>=`, or recording the rejected attempt fails this check.

## N3 — Historical negative business result versus conflict

Under a valid lease with job `k = READY`, submit `q2 = (COMPLETE, k, w)`. Record the implementation’s documented nonmutating “not claimed” response and confirm one history entry. Reuse ID `q2` for `(CLAIM, k, w)`; expect `ID_CONFLICT`, `k` still `READY`, and the original entry unchanged. Claim `k` with a new ID, then replay the original `q2`; expect the exact original “not claimed” response even though `k` is now claimed, with no new mutation.

## N4 — Historical replay cannot resurrect state after failover

1. Under A’s valid lease, accept `q3 = (CLAIM, m, w)` and then `q4 = (COMPLETE, m, w)`; expect `m = DONE(w)`.
2. At A’s expiry, install B’s next lease.
3. Retry exact `q3` using A’s stale lease.

Expect the exact historical `OK_CLAIMED` response from q3, while the live job remains `DONE(w)`, history cardinality remains two, and the log records a replay rather than a new claim. Returning `FENCED` here violates the specified history-first contract; returning `OK_CLAIMED` while reverting state is a critical failure.

## N5 — Same-tick insertion order is observable and reversible

In a fresh simulator with one valid dispatcher, schedule at the same tick:

- `q5 = (CLAIM, n, w1)` first;
- `q6 = (CLAIM, n, w2)` second.

Expect `w1` to own the claim, one state-changing decision, both authorized requests recorded, and logs ordered by their distinct insertion indices. Repeat in another fresh simulator with insertion order reversed; expect `w2` to own the claim. Repeating either setup at least 20 times must give the same result and structural log. Sorting by command ID, worker, hash order, or object identity fails.

## N6 — Grant failure leaves no split publication

Record coordinator epoch/current lease and queue active fence. First request TTL 0 and then a non-integer TTL; each must be rejected with all recorded state unchanged. If the design exposes a fence-install seam, replace it temporarily with a stub that raises before mutation and attempt the next otherwise valid grant. The exception or error may propagate, but coordinator epoch/current lease and queue fence must remain at the recorded values. Restore the seam before other checks.

If no safe seam exists, inspect and report whether the failure-atomicity claim can be dynamically verified; do not silently award the atomic failure-path item from prose alone.

## N7 — Expiry without a successor

Grant A for `[10,13)`. With no successor grant, submit an unseen request at tick 13 using A’s exact installed lease. Expect `FENCED` (or a node-side `NO_LEASE` before the queue), no job/history mutation, and a diagnostic that identifies expiry. Directly exercise the queue as well; it must independently return `FENCED`. This distinguishes authoritative interval checking from merely replacing old epochs on a later grant.

## N8 — Logging is observational and complete

Run a combined trace containing a denied grant, successful fence install, node expiry rejection, queue fence rejection, accepted mutation, exact replay, payload conflict, and nonmutating business result. Check that applicable records contain all required keys with explicit nulls, presented and active authority are distinguishable, and record order matches model-event order.

Run the same trace with collection disabled or redirected through the learner’s supported hook. Responses, state, history, and fence must match the logged run exactly. Timestamps, memory addresses, unordered serialization, or behavior changes caused by logging are defects.

## Examiner boundary report

End the novel-check record with:

- submission digests and the adapter digest, if any;
- observed results for N1–N8, including failures rather than only a summary;
- whether the evidence is reproducible under the bounded harness;
- the explicit statement `course_completion: NOT_CLAIMED`.

Do not extrapolate these semantic-model results to real-clock lease safety, distributed consensus, storage durability, production deployment, an official course unit, or transfer of knowledge.
